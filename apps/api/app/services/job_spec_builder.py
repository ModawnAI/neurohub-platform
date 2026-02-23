"""Builds a Job Spec JSON from Request snapshots + Case data for the compute worker."""

import uuid
from typing import Any

from app.config import settings
from app.models.request import Case, Request


def build_job_spec(
    run_id: uuid.UUID,
    request: Request,
    case: Case,
) -> dict[str, Any]:
    """Build a complete Job Spec for a pipeline execution.

    Combines the frozen service/pipeline snapshots stored on the Request
    with the Case's demographics and file artifacts.

    The resulting dict is stored in Run.job_spec and sent to the worker.
    It contains everything needed to execute the pipeline without further DB lookups.
    """
    pipeline_snap = request.pipeline_snapshot or {}
    service_snap = request.service_snapshot or {}

    # Build input artifacts from case files
    input_artifacts: dict[str, str] = {}
    for cf in case.files:
        if cf.upload_status == "COMPLETED" and cf.storage_path:
            input_artifacts[cf.slot_name] = cf.storage_path

    # Build steps from pipeline snapshot
    raw_steps = pipeline_snap.get("steps", [])
    steps = []
    for i, step in enumerate(raw_steps):
        steps.append(
            {
                "index": i,
                "name": step.get("name", f"step_{i}"),
                "image": step.get("image", "unknown:latest"),
                "command": step.get("command"),
                "resources": step.get("resources", {"gpu": 0, "memory_gb": 8}),
                "timeout_seconds": step.get("timeout_seconds", settings.compute_step_timeout),
            }
        )

    # Output destination
    institution_id = str(request.institution_id)
    output_base = (
        f"institutions/{institution_id}/requests/{request.id}/cases/{case.id}/outputs"
    )

    return {
        "run_id": str(run_id),
        "request_id": str(request.id),
        "case_id": str(case.id),
        "institution_id": institution_id,
        "service_id": str(request.service_id),
        "service": {
            "name": service_snap.get("name"),
            "display_name": service_snap.get("display_name"),
            "version": service_snap.get("version"),
        },
        "pipeline": {
            "name": pipeline_snap.get("name"),
            "version": pipeline_snap.get("version"),
        },
        "priority": request.priority,
        "user_inputs": request.inputs,
        "user_options": request.options,
        "case_demographics": case.demographics,
        "patient_ref": case.patient_ref,
        "input_artifacts": input_artifacts,
        "steps": steps,
        "qc_rules": pipeline_snap.get("qc_rules"),
        "resource_requirements": pipeline_snap.get("resource_requirements"),
        "storage": {
            "bucket_inputs": settings.storage_bucket_inputs,
            "bucket_outputs": settings.storage_bucket_outputs,
            "bucket_reports": settings.storage_bucket_reports,
            "output_base": output_base,
        },
        "callback_url": f"/internal/runs/{run_id}/result",
        "heartbeat_url": f"/internal/runs/{run_id}/heartbeat",
    }
