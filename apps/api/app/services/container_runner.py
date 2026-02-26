"""Container Runner — Fly Machine API orchestrator for running service containers.

Manages the lifecycle of Fly Machines that execute NeuroHub service containers:
- Launch machines with JobSpec
- Monitor machine status
- Collect logs and results
- Handle timeouts and cleanup
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger("neurohub.container_runner")


class ContainerStatus(str, Enum):
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "started"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    DESTROYED = "destroyed"

    @classmethod
    def from_fly_state(cls, state: str) -> "ContainerStatus":
        mapping = {
            "created": cls.CREATED,
            "starting": cls.STARTING,
            "started": cls.RUNNING,
            "stopping": cls.STOPPING,
            "stopped": cls.STOPPED,
            "failed": cls.FAILED,
            "destroyed": cls.DESTROYED,
        }
        return mapping.get(state, cls.FAILED)


@dataclass
class ContainerConfig:
    """Configuration for a Fly Machine derived from a pipeline step."""

    image: str
    memory_mb: int = 1024
    cpus: int = 1
    cpu_kind: str = "shared"
    gpu_kind: str | None = None
    gpus: int = 0
    timeout_seconds: int = 300

    @classmethod
    def from_step(cls, step: dict, job_spec: dict) -> "ContainerConfig":
        if not step.get("image"):
            raise ValueError("Step must specify a container 'image'")
        resources = step.get("resources", {})
        memory_gb = resources.get("memory_gb", 1)
        gpu = resources.get("gpu", 0)

        if gpu > 0:
            return cls(
                image=step["image"],
                memory_mb=int(memory_gb * 1024),
                cpus=max(4, resources.get("cpus", 4)),
                cpu_kind="performance",
                gpu_kind=resources.get("gpu_kind", "a100-pcie-40gb"),
                gpus=gpu,
                timeout_seconds=step.get("timeout_seconds", 600),
            )

        return cls(
            image=step["image"],
            memory_mb=int(memory_gb * 1024),
            cpus=resources.get("cpus", 1),
            cpu_kind="shared",
            timeout_seconds=step.get("timeout_seconds", 300),
        )


@dataclass
class MachineSpec:
    """Full specification for creating a Fly Machine."""

    config: ContainerConfig
    job_spec: dict
    env: dict[str, str] = field(default_factory=dict)
    region: str = "nrt"

    def to_fly_payload(self) -> dict[str, Any]:
        guest: dict[str, Any] = {
            "memory_mb": self.config.memory_mb,
            "cpus": self.config.cpus,
            "cpu_kind": self.config.cpu_kind,
        }
        if self.config.gpus > 0 and self.config.gpu_kind:
            guest["gpus"] = self.config.gpus
            guest["gpu_kind"] = self.config.gpu_kind

        return {
            "region": self.region,
            "config": {
                "image": self.config.image,
                "guest": guest,
                "env": self.env,
                "auto_destroy": True,
                "restart": {"policy": "no"},
            },
        }


@dataclass
class RunResult:
    """Result of a container execution."""

    machine_id: str
    status: str  # SUCCEEDED, FAILED, TIMEOUT
    logs: str = ""
    exit_code: int | None = None
    duration_ms: int = 0
    error: str | None = None


@dataclass
class LaunchResult:
    """Result of launching a machine."""

    machine_id: str
    instance_id: str | None = None


class ContainerRunner:
    """Orchestrates Fly Machine API calls for service container execution."""

    def __init__(
        self,
        fly_api_token: str,
        fly_org: str = "neurohub",
        api_base_url: str = "https://api.machines.dev",
    ):
        self.fly_api_token = fly_api_token
        self.fly_org = fly_org
        self.api_base_url = api_base_url

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.fly_api_token}",
            "Content-Type": "application/json",
        }

    async def launch_machine(
        self,
        app_name: str,
        job_spec: dict,
        step_index: int = 0,
        region: str = "nrt",
    ) -> LaunchResult:
        """Create and start a Fly Machine for the given step."""
        import httpx

        step = job_spec.get("steps", [])[step_index] if job_spec.get("steps") else {}
        config = ContainerConfig.from_step(step, job_spec)

        # Encode job spec as env variable
        job_spec_b64 = base64.b64encode(json.dumps(job_spec).encode()).decode()

        env = {
            "NEUROHUB_JOB_SPEC": job_spec_b64,
            "NEUROHUB_RUN_ID": job_spec.get("run_id", ""),
            "NEUROHUB_STEP_INDEX": str(step_index),
        }

        spec = MachineSpec(config=config, job_spec=job_spec, env=env, region=region)
        payload = spec.to_fly_payload()

        url = f"{self.api_base_url}/v1/apps/{app_name}/machines"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        machine_id = data["id"]
        logger.info("Launched machine %s for app %s", machine_id, app_name)
        return LaunchResult(machine_id=machine_id, instance_id=data.get("instance_id"))

    async def get_machine_status(self, app_name: str, machine_id: str) -> ContainerStatus:
        """Get current machine status."""
        import httpx

        url = f"{self.api_base_url}/v1/apps/{app_name}/machines/{machine_id}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        return ContainerStatus.from_fly_state(data["state"])

    async def wait_for_machine(
        self,
        app_name: str,
        machine_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300,
    ) -> ContainerStatus:
        """Poll machine until it reaches a terminal state."""
        start = time.monotonic()
        terminal = {ContainerStatus.STOPPED, ContainerStatus.FAILED, ContainerStatus.DESTROYED}

        while time.monotonic() - start < timeout:
            status = await self.get_machine_status(app_name, machine_id)
            if status in terminal:
                return status
            await asyncio.sleep(poll_interval)

        return ContainerStatus.STOPPED  # Will be caught as timeout by caller

    async def get_machine_logs(self, app_name: str, machine_id: str) -> str:
        """Retrieve logs from a machine."""
        import httpx

        url = f"{self.api_base_url}/v1/apps/{app_name}/machines/{machine_id}/logs"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.text
            return ""

    async def destroy_machine(self, app_name: str, machine_id: str) -> None:
        """Destroy a machine (cleanup)."""
        import httpx

        url = f"{self.api_base_url}/v1/apps/{app_name}/machines/{machine_id}"
        async with httpx.AsyncClient(timeout=10) as client:
            await client.delete(url, headers=self._headers())
        logger.info("Destroyed machine %s", machine_id)

    async def execute_step(
        self,
        app_name: str,
        job_spec: dict,
        step_index: int = 0,
        timeout_override: float | None = None,
    ) -> RunResult:
        """Full lifecycle: launch → wait → collect logs → return result."""
        start = time.monotonic()

        step = job_spec.get("steps", [{}])[step_index] if job_spec.get("steps") else {}
        timeout = timeout_override or step.get("timeout_seconds", 300)

        try:
            launch = await self.launch_machine(app_name, job_spec, step_index)
        except Exception as e:
            return RunResult(
                machine_id="",
                status="FAILED",
                error=f"Launch failed: {e}",
            )

        try:
            status = await self.wait_for_machine(
                app_name,
                launch.machine_id,
                poll_interval=min(2.0, timeout / 10),
                timeout=timeout,
            )
        except Exception as e:
            status = ContainerStatus.FAILED

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # Check timeout
        if time.monotonic() - start >= timeout:
            try:
                await self.destroy_machine(app_name, launch.machine_id)
            except Exception:
                pass
            return RunResult(
                machine_id=launch.machine_id,
                status="TIMEOUT",
                duration_ms=elapsed_ms,
                error=f"Machine exceeded timeout of {timeout}s",
            )

        # Collect logs
        try:
            logs = await self.get_machine_logs(app_name, launch.machine_id)
        except Exception:
            logs = ""

        # Map terminal status
        if status == ContainerStatus.STOPPED:
            result_status = "SUCCEEDED"
        elif status == ContainerStatus.FAILED:
            result_status = "FAILED"
        else:
            result_status = status.value.upper()

        # Cleanup
        try:
            await self.destroy_machine(app_name, launch.machine_id)
        except Exception:
            pass

        return RunResult(
            machine_id=launch.machine_id,
            status=result_status,
            logs=logs,
            duration_ms=elapsed_ms,
        )

    async def run_job(self, job_spec: dict, timeout_seconds: int = 1800) -> dict:
        """High-level: launch machine, wait for completion, collect logs, destroy.

        Returns dict with 'logs', 'exit_code', 'status'.
        Executes all steps sequentially and aggregates logs.
        """
        steps = job_spec.get("steps", [{}])
        app_name = app_name_from_job_spec(job_spec)
        all_logs: list[str] = []
        final_exit_code = 0

        for step_index in range(len(steps)):
            result = await self.execute_step(
                app_name=app_name,
                job_spec=job_spec,
                step_index=step_index,
                timeout_override=float(timeout_seconds),
            )
            if result.logs:
                all_logs.append(result.logs)

            if result.status == "TIMEOUT":
                return {
                    "logs": "\n".join(all_logs),
                    "exit_code": 124,
                    "status": "TIMEOUT",
                    "error": result.error,
                }
            if result.status != "SUCCEEDED":
                return {
                    "logs": "\n".join(all_logs),
                    "exit_code": result.exit_code or 1,
                    "status": "FAILED",
                    "error": result.error,
                }

        return {
            "logs": "\n".join(all_logs),
            "exit_code": final_exit_code,
            "status": "SUCCEEDED",
        }

    async def enrich_input_urls(
        self,
        job_spec: dict,
        sign_fn: Callable[[str, str], Awaitable[str]],
    ) -> dict:
        """Add presigned download URLs for input artifacts to the job spec."""
        enriched = dict(job_spec)
        artifacts = job_spec.get("input_artifacts", {})
        storage = job_spec.get("storage", {})
        bucket = storage.get("bucket_inputs", "neurohub-inputs")

        presigned_urls = {}
        for slot_key, storage_path in artifacts.items():
            presigned_urls[slot_key] = await sign_fn(bucket, storage_path)

        enriched["presigned_urls"] = presigned_urls
        return enriched


def service_to_app_name(service_name: str) -> str:
    """Convert a service name to a Fly app name."""
    sanitized = re.sub(r"[^a-z0-9-]", "-", service_name.lower()).strip("-")
    # Collapse multiple hyphens
    sanitized = re.sub(r"-+", "-", sanitized)
    return f"neurohub-svc-{sanitized}"


def app_name_from_job_spec(job_spec: dict) -> str:
    """Extract the Fly app name from a JobSpec."""
    service = job_spec.get("service", {})
    name = service.get("name", "unknown")
    return service_to_app_name(name)
