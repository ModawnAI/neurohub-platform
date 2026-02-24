"""Pipeline dispatch: creates Runs with JobSpecs and dispatches to workers.

Called when a request transitions to READY_TO_COMPUTE → COMPUTING.
"""

import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.config import settings
from app.database import sync_session_factory
from app.models.outbox import OutboxEvent
from app.models.request import Request
from app.models.run import Run, RunStep
from app.services.job_spec_builder import build_job_spec
from app.worker.celery_app import celery_app

logger = logging.getLogger("neurohub.pipeline")


@celery_app.task(
    name="neurohub.tasks.dispatch_pipeline",
    bind=True,
    max_retries=2,
    default_retry_delay=15,
    queue="compute",
)
def dispatch_pipeline(self, request_id: str) -> dict:
    """Create Runs for each Case, build JobSpecs, and dispatch to workers.

    1. Load request + cases
    2. Transition request to COMPUTING
    3. For each case: create Run, build JobSpec, create RunSteps
    4. Dispatch each run (Celery task or external HTTP callback)
    """
    logger.info("Dispatching pipeline for request %s", request_id)

    with sync_session_factory() as session:
        request = session.execute(
            select(Request)
            .where(Request.id == uuid.UUID(request_id))
            .with_for_update()
        ).scalar_one_or_none()

        if not request:
            logger.error("Request %s not found", request_id)
            return {"error": "Request not found"}

        if request.status != "READY_TO_COMPUTE":
            logger.warning(
                "Request %s in status %s, expected READY_TO_COMPUTE",
                request_id,
                request.status,
            )
            return {"request_id": request_id, "status": request.status}

        # Transition to COMPUTING
        request.status = "COMPUTING"

        cases = list(request.cases)
        if not cases:
            logger.error("Request %s has no cases", request_id)
            request.status = "FAILED"
            request.error_detail = "No cases found for pipeline execution"
            session.commit()
            return {"error": "No cases"}

        pipeline_snap = request.pipeline_snapshot or {}
        raw_steps = pipeline_snap.get("steps", [])
        run_ids: list[str] = []

        for case in cases:
            run = Run(
                institution_id=request.institution_id,
                request_id=request.id,
                case_id=case.id,
                status="PENDING",
                priority=request.priority,
            )
            session.add(run)
            session.flush()  # get run.id

            # Build JobSpec
            job_spec = build_job_spec(run.id, request, case)
            run.job_spec = job_spec

            # Create RunSteps from pipeline definition
            for i, step_def in enumerate(raw_steps):
                session.add(
                    RunStep(
                        run_id=run.id,
                        step_index=i,
                        step_name=step_def.get("name", f"step_{i}"),
                        status="PENDING",
                        docker_image=step_def.get("image"),
                    )
                )

            request.current_run_id = run.id
            run_ids.append(str(run.id))

        session.add(
            OutboxEvent(
                event_type="PIPELINE_DISPATCHED",
                aggregate_type="request",
                aggregate_id=request.id,
                payload={
                    "request_id": request_id,
                    "run_ids": run_ids,
                },
            )
        )
        session.commit()

    # Dispatch runs to workers (outside DB transaction)
    for rid in run_ids:
        _dispatch_run(rid)

    logger.info("Dispatched %d runs for request %s", len(run_ids), request_id)
    return {"request_id": request_id, "run_ids": run_ids}


def _dispatch_run(run_id: str) -> None:
    """Dispatch a single run to either Celery or external compute."""
    if settings.external_compute_url:
        _dispatch_external(run_id)
    else:
        _dispatch_celery(run_id)


def _dispatch_celery(run_id: str) -> None:
    """Dispatch run to the local Celery worker."""
    celery_app.send_task(
        "neurohub.tasks.execute_run",
        args=[run_id],
        queue="compute",
    )
    logger.info("Dispatched run %s to Celery compute queue", run_id)


def _dispatch_external(run_id: str) -> None:
    """Dispatch run to an external GPU server via HTTP callback.

    Sends the JobSpec to the external compute URL. The external server
    is expected to call back to /internal/runs/{run_id}/result when done,
    and send heartbeats to /internal/runs/{run_id}/heartbeat periodically.
    """
    with sync_session_factory() as session:
        run = session.execute(
            select(Run).where(Run.id == uuid.UUID(run_id))
        ).scalar_one_or_none()

        if not run or not run.job_spec:
            logger.error("Run %s not found or has no job_spec", run_id)
            return

        job_spec = run.job_spec
        run.status = "RUNNING"
        run.started_at = datetime.now(timezone.utc)
        run.heartbeat_at = datetime.now(timezone.utc)
        session.commit()

    try:
        resp = httpx.post(
            settings.external_compute_url,
            json=job_spec,
            headers={"X-Internal-Key": settings.internal_api_key},
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("Dispatched run %s to external compute: %s", run_id, resp.status_code)
    except Exception:
        logger.exception("Failed to dispatch run %s to external compute", run_id)
        # Fall back to Celery
        with sync_session_factory() as session:
            run = session.execute(
                select(Run).where(Run.id == uuid.UUID(run_id))
            ).scalar_one()
            run.status = "PENDING"
            run.started_at = None
            session.commit()
        _dispatch_celery(run_id)
