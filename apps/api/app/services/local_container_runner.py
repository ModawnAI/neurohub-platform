"""Local Container Runner — executes technique containers via local Docker daemon.

For self-hosted servers where neuroimaging tools (FreeSurfer, FSL, MRtrix3) are
installed natively. Containers are lightweight Python wrappers that mount the
host tool directories as read-only volumes.

Usage:
    runner = LocalContainerRunner()
    exit_code, logs = await runner.execute_technique(
        technique_key="Cortical_Thickness",
        docker_image="neurohub/cortical-thickness:1.0.0",
        input_dir="/data/bids/sub-001",
        output_dir="/data/outputs/ct",
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings

logger = logging.getLogger("neurohub.local_container_runner")

# Default host mounts for neuroimaging tools
DEFAULT_HOST_MOUNTS: dict[str, str] = {
    "/usr/local/freesurfer/8.0.0": "/opt/freesurfer",
    "/usr/local/fsl": "/opt/fsl",
    "/usr/local/mrtrix3": "/opt/mrtrix3",
    # FDG-PET analysis (MATLAB/SPM25/neuroan_pet)
    "/usr/local/MATLAB/R2025b": "/opt/matlab",
    "/projects4/environment/codes/spm25": "/opt/spm25",
    "/projects4/environment/codes/neuroan_pet": "/opt/neuroan_pet",
    "/projects4/NEUROHUB/TEST/DB": "/opt/neuroan_db",
}


@dataclass
class LocalRunResult:
    """Result of a local Docker container execution."""

    exit_code: int
    logs: str
    duration_ms: int = 0
    technique_output: dict | None = None


def parse_host_mounts() -> dict[str, str]:
    """Parse host mounts from settings or use defaults."""
    configured = settings.local_docker_host_mounts
    if configured:
        try:
            return json.loads(configured)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Invalid local_docker_host_mounts, using defaults")

    return DEFAULT_HOST_MOUNTS


class LocalContainerRunner:
    """Execute technique containers via local Docker daemon."""

    def __init__(self, host_mounts: dict[str, str] | None = None):
        self.host_mounts = host_mounts or parse_host_mounts()

    # Techniques that require --net=host (e.g. for MATLAB license validation)
    NET_HOST_TECHNIQUES = {"FDG_PET"}

    async def execute_technique(
        self,
        technique_key: str,
        docker_image: str,
        input_dir: str,
        output_dir: str,
        job_spec: dict | None = None,
        extra_env: dict[str, str] | None = None,
        timeout: int = 7200,
        gpu: bool = False,
        extra_mounts: dict[str, str] | None = None,
        net_host: bool | None = None,
    ) -> LocalRunResult:
        """Execute a technique container and return results.

        Args:
            technique_key: e.g. "Cortical_Thickness"
            docker_image: e.g. "neurohub/cortical-thickness:1.0.0"
            input_dir: path to BIDS input directory
            output_dir: path to output directory
            job_spec: optional JSON job spec (passed as NEUROHUB_JOB_SPEC env)
            extra_env: additional environment variables
            timeout: max execution time in seconds
            gpu: enable GPU access
            extra_mounts: additional host:container mount pairs
        """
        import time

        start = time.monotonic()

        # Ensure output dir exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Build docker run command
        cmd = ["docker", "run", "--rm"]

        # Host networking for MATLAB license validation
        use_net_host = net_host if net_host is not None else (
            technique_key in self.NET_HOST_TECHNIQUES
        )
        if use_net_host:
            cmd.extend(["--net", "host"])

        # Mount input/output
        cmd.extend(["-v", f"{input_dir}:/input:ro"])
        cmd.extend(["-v", f"{output_dir}:/output"])

        # Mount host tools (read-only)
        all_mounts = {**self.host_mounts}
        if extra_mounts:
            all_mounts.update(extra_mounts)

        for host_path, container_path in all_mounts.items():
            if Path(host_path).exists():
                cmd.extend(["-v", f"{host_path}:{container_path}:ro"])
            else:
                logger.warning(f"Host mount not found: {host_path}")

        # Environment variables
        env_vars: dict[str, str] = {}
        if job_spec:
            import base64

            spec_json = json.dumps(job_spec)
            spec_b64 = base64.b64encode(spec_json.encode()).decode()
            env_vars["NEUROHUB_JOB_SPEC"] = spec_b64

        if extra_env:
            env_vars.update(extra_env)

        for key, val in env_vars.items():
            cmd.extend(["-e", f"{key}={val}"])

        # GPU support
        if gpu:
            cmd.extend(["--gpus", "all"])

        # Memory limit
        cmd.extend(["--memory", "16g"])

        # Image
        cmd.append(docker_image)

        logger.info(f"Executing technique {technique_key}: {docker_image}")
        logger.info(f"Input: {input_dir}, Output: {output_dir}")

        # Run container
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                duration = int((time.monotonic() - start) * 1000)
                return LocalRunResult(
                    exit_code=124,
                    logs=f"Container timed out after {timeout}s",
                    duration_ms=duration,
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            logs = stdout + ("\n--- STDERR ---\n" + stderr if stderr.strip() else "")
            duration = int((time.monotonic() - start) * 1000)

            # Parse NEUROHUB_OUTPUT from logs
            technique_output = None
            for line in stdout.splitlines():
                if line.startswith("NEUROHUB_OUTPUT:"):
                    try:
                        json_str = line[len("NEUROHUB_OUTPUT:"):].strip()
                        technique_output = json.loads(json_str)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse NEUROHUB_OUTPUT: {line[:200]}")

            result = LocalRunResult(
                exit_code=proc.returncode or 0,
                logs=logs[-5000:],  # Keep last 5000 chars
                duration_ms=duration,
                technique_output=technique_output,
            )

            if result.exit_code != 0:
                logger.error(
                    f"Container {technique_key} failed (exit={result.exit_code}): "
                    f"{stderr[-500:]}"
                )
            else:
                logger.info(
                    f"Container {technique_key} completed in {duration}ms, "
                    f"output={'found' if technique_output else 'missing'}"
                )

            return result

        except FileNotFoundError:
            duration = int((time.monotonic() - start) * 1000)
            return LocalRunResult(
                exit_code=127,
                logs="Docker command not found. Is Docker installed?",
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            logger.exception(f"Container execution error: {e}")
            return LocalRunResult(
                exit_code=1,
                logs=f"Execution error: {e}",
                duration_ms=duration,
            )

    async def check_image_exists(self, docker_image: str) -> bool:
        """Check if a Docker image exists locally."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "image", "inspect", docker_image,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False

    async def pull_image(self, docker_image: str) -> bool:
        """Pull a Docker image."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "pull", docker_image,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False
