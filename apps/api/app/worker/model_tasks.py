"""Celery tasks for model artifact scanning and image building."""
import logging
import re
import uuid
from datetime import datetime, timezone

from app.worker.celery_app import celery_app

logger = logging.getLogger("neurohub.model_tasks")


@celery_app.task(
    name="neurohub.tasks.scan_artifact",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="scanner",
)
def scan_artifact(self, artifact_id: str):
    """Run security scans on an uploaded artifact."""
    import httpx
    from app.database import sync_session_factory
    from app.models.model_artifact import ModelArtifact
    from app.services.code_scanner import (
        check_sha256,
        determine_overall_status,
        run_bandit,
        scan_python_ast,
        scan_requirements,
    )

    with sync_session_factory() as db:
        artifact = db.get(ModelArtifact, uuid.UUID(artifact_id))
        if not artifact:
            logger.error("Artifact %s not found", artifact_id)
            return

        artifact.status = "SCANNING"
        db.commit()

        try:
            from app.config import settings
            url = f"{settings.supabase_url}/storage/v1/object/model-artifacts/{artifact.storage_path}"
            resp = httpx.get(url, headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
            }, timeout=60)
            resp.raise_for_status()
            content = resp.content

            # Verify checksum
            actual_sha = check_sha256(content)
            if artifact.checksum_sha256 and actual_sha != artifact.checksum_sha256:
                _save_scan(db, artifact.id, "checksum", "FAIL", "CRITICAL",
                           [{"rule": "CHECKSUM_MISMATCH", "severity": "CRITICAL",
                             "message": "File checksum does not match uploaded value"}])
                artifact.status = "REJECTED"
                db.commit()
                return

            all_findings = []

            if artifact.artifact_type == "script":
                source = content.decode("utf-8", errors="replace")
                ast_findings = scan_python_ast(source)
                _save_scan(db, artifact.id, "ast_check",
                           *determine_overall_status(ast_findings), ast_findings)
                all_findings.extend(ast_findings)

                bandit_findings = run_bandit(source)
                _save_scan(db, artifact.id, "bandit",
                           *determine_overall_status(bandit_findings), bandit_findings)
                all_findings.extend(bandit_findings)

            elif artifact.artifact_type == "requirements":
                source = content.decode("utf-8", errors="replace")
                req_findings = scan_requirements(source)
                _save_scan(db, artifact.id, "allowlist",
                           *determine_overall_status(req_findings), req_findings)
                all_findings.extend(req_findings)

            overall_status, max_severity = determine_overall_status(all_findings)
            critical_findings = [f for f in all_findings
                                  if f.get("severity") in ("CRITICAL", "HIGH")]

            if critical_findings:
                artifact.status = "REJECTED"
                artifact.review_notes = (
                    f"Auto-rejected: {len(critical_findings)} critical/high severity issues found"
                )
            else:
                artifact.status = "APPROVED"

            db.commit()
            logger.info("Artifact %s scanned: %s (%d findings)",
                        artifact_id, artifact.status, len(all_findings))

        except Exception as e:
            logger.exception("Scan failed for artifact %s: %s", artifact_id, e)
            artifact.status = "PENDING_SCAN"
            db.commit()
            raise self.retry(exc=e)


def _save_scan(db, artifact_id, scanner, status, severity, findings):
    from app.models.model_artifact import CodeSecurityScan
    scan = CodeSecurityScan(
        artifact_id=artifact_id,
        scanner=scanner,
        status=status,
        severity=severity,
        findings=findings,
        scanned_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    db.flush()


@celery_app.task(
    name="neurohub.tasks.build_service_image",
    bind=True,
    max_retries=1,
    queue="builder",
    time_limit=1800,  # 30 min max
)
def build_service_image(self, artifact_id: str):
    """Build Docker image from approved artifact and push to registry."""
    import os
    import subprocess
    import tempfile

    import httpx

    from app.config import settings
    from app.database import sync_session_factory
    from app.models.model_artifact import ModelArtifact

    with sync_session_factory() as db:
        artifact = db.get(ModelArtifact, uuid.UUID(artifact_id))
        if not artifact or artifact.status != "APPROVED":
            return

        artifact.build_status = "BUILDING"
        db.commit()

        try:
            base_images = {
                "pytorch": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
                "tensorflow": "tensorflow/tensorflow:2.14.0",
                "python3.11": "python:3.11-slim",
                "onnxruntime": "python:3.11-slim",
            }
            base_image = base_images.get(artifact.runtime or "python3.11", "python:3.11-slim")

            from app.models.service import ServiceDefinition
            svc = db.get(ServiceDefinition, artifact.service_id)
            svc_name = (
                re.sub(r"[^a-z0-9-]", "-", svc.name.lower())
                if svc else str(artifact.service_id)[:8]
            )
            image_tag = f"registry.fly.io/neurohub-svc-{svc_name}:artifact-{str(artifact.id)[:8]}"

            with tempfile.TemporaryDirectory() as tmpdir:
                _download_artifact(artifact, tmpdir, settings)

                dockerfile_content = _generate_dockerfile(base_image, artifact)
                dockerfile_path = os.path.join(tmpdir, "Dockerfile")
                with open(dockerfile_path, "w") as f:
                    f.write(dockerfile_content)

                build_log_lines = []
                result = subprocess.run(
                    ["docker", "build", "-t", image_tag, tmpdir],
                    capture_output=True, text=True, timeout=1200
                )
                build_log_lines.append(result.stdout[-5000:] if result.stdout else "")
                build_log_lines.append(result.stderr[-2000:] if result.stderr else "")

                if result.returncode != 0:
                    artifact.build_status = "FAILED"
                    artifact.build_log = "\n".join(build_log_lines)
                    db.commit()
                    return

                push_result = subprocess.run(
                    ["docker", "push", image_tag],
                    capture_output=True, text=True, timeout=600
                )
                if push_result.returncode != 0:
                    artifact.build_status = "FAILED"
                    artifact.build_log = push_result.stderr[-2000:]
                    db.commit()
                    return

                artifact.container_image = image_tag
                artifact.build_status = "BUILT"
                artifact.build_log = "\n".join(build_log_lines)

                _update_pipeline_image(db, artifact.service_id, image_tag)

            db.commit()
            logger.info("Built image %s for artifact %s", image_tag, artifact_id)

        except Exception as e:
            logger.exception("Build failed for artifact %s: %s", artifact_id, e)
            artifact.build_status = "FAILED"
            artifact.build_log = str(e)
            db.commit()
            raise self.retry(exc=e)


def _download_artifact(artifact, tmpdir, settings):
    import os

    import httpx

    url = f"{settings.supabase_url}/storage/v1/object/model-artifacts/{artifact.storage_path}"
    resp = httpx.get(url, headers={
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }, timeout=120)
    resp.raise_for_status()
    dest_path = os.path.join(tmpdir, artifact.file_name)
    with open(dest_path, "wb") as f:
        f.write(resp.content)


def _generate_dockerfile(base_image: str, artifact) -> str:
    lines = [
        f"FROM {base_image}",
        "WORKDIR /app",
        "RUN mkdir -p /input /output /model",
    ]
    if artifact.artifact_type == "requirements":
        lines += [
            f"COPY {artifact.file_name} /app/requirements.txt",
            "RUN pip install --no-cache-dir -r /app/requirements.txt",
        ]
    elif artifact.artifact_type == "script":
        lines += [
            f"COPY {artifact.file_name} /app/inference.py",
        ]
    elif artifact.artifact_type == "weights":
        lines += [
            f"COPY {artifact.file_name} /model/{artifact.file_name}",
        ]
    lines += [
        "RUN pip install --no-cache-dir neurohub-sdk 2>/dev/null || true",
        'CMD ["python", "/app/inference.py"]',
    ]
    return "\n".join(lines)


def _update_pipeline_image(db, service_id, image_tag):
    from sqlalchemy import select

    from app.models.service import PipelineDefinition

    pipelines = db.execute(
        select(PipelineDefinition).where(PipelineDefinition.service_id == service_id)
    ).scalars().all()
    for pipeline in pipelines:
        if pipeline.steps:
            updated = []
            for step in pipeline.steps:
                step["image"] = image_tag
                updated.append(step)
            pipeline.steps = updated
    db.flush()
