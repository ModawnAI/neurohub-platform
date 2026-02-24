"""Internal Worker Callback API.

These endpoints are called by compute workers (Celery tasks or external GPU servers)
to report results and heartbeats. Authenticated via INTERNAL_API_KEY, not user JWT.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.notification import Notification
from app.models.outbox import OutboxEvent
from app.models.request import Request
from app.models.run import Run
from app.services.qc_evaluator import evaluate_qc
from app.services.state_machine import RequestStatus

logger = logging.getLogger("neurohub.internal")

router = APIRouter(prefix="/internal", tags=["internal"])


# ---------------------------------------------------------------------------
# Auth dependency — INTERNAL_API_KEY
# ---------------------------------------------------------------------------
async def verify_internal_key(
    x_internal_key: str | None = Header(default=None),
) -> None:
    """Verify the request carries a valid internal API key."""
    if not settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API not configured",
        )
    if not x_internal_key or x_internal_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class RunResultPayload(BaseModel):
    status: str = Field(..., pattern="^(SUCCEEDED|FAILED)$")
    result_manifest: dict | None = None
    error_detail: str | None = None


class HeartbeatPayload(BaseModel):
    worker_id: str | None = None
    progress_pct: float | None = Field(default=None, ge=0, le=100)
    current_step: str | None = None


class RunResultResponse(BaseModel):
    run_id: str
    request_id: str
    request_status: str


class HeartbeatResponse(BaseModel):
    run_id: str
    acknowledged: bool = True


# ---------------------------------------------------------------------------
# POST /internal/runs/{run_id}/result
# ---------------------------------------------------------------------------
@router.post(
    "/runs/{run_id}/result",
    response_model=RunResultResponse,
    dependencies=[Depends(verify_internal_key)],
)
async def report_run_result(
    run_id: uuid.UUID,
    payload: RunResultPayload,
    db: AsyncSession = Depends(get_db),
) -> RunResultResponse:
    """Worker reports computation result (success or failure)."""
    run = (
        await db.execute(
            select(Run).where(Run.id == run_id).with_for_update()
        )
    ).scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in ("PENDING", "RUNNING"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run already in terminal state: {run.status}",
        )

    now = datetime.now(timezone.utc)

    if payload.status == "SUCCEEDED":
        run.status = "SUCCEEDED"
        run.result_manifest = payload.result_manifest
        run.completed_at = now
    else:
        run.status = "FAILED"
        run.error_detail = (payload.error_detail or "Worker reported failure")[:2000]
        run.completed_at = now

    await db.flush()

    # Check if all runs for this request are done
    request = (
        await db.execute(
            select(Request).where(Request.id == run.request_id).with_for_update()
        )
    ).scalar_one()

    all_runs = (
        await db.execute(select(Run).where(Run.request_id == request.id))
    ).scalars().all()

    all_done = all(r.status in ("SUCCEEDED", "FAILED") for r in all_runs)

    if all_done and request.status == "COMPUTING":
        any_failed = any(r.status == "FAILED" for r in all_runs)

        if any_failed:
            request.status = RequestStatus.FAILED.value
            request.error_detail = "One or more pipeline runs failed"
            _add_notification(
                db,
                request,
                "COMPUTING_FAILED",
                "분석 실패",
                "하나 이상의 분석 작업이 실패했습니다.",
            )
        else:
            # Evaluate QC to decide next state
            completed_run = next(r for r in all_runs if r.status == "SUCCEEDED")
            qc_rules = (request.pipeline_snapshot or {}).get("qc_rules")
            next_status = evaluate_qc(completed_run.result_manifest, qc_rules)
            request.status = next_status.value

            if next_status == RequestStatus.QC:
                _add_notification(
                    db,
                    request,
                    "QC_REQUIRED",
                    "품질 검증 필요",
                    "분석이 완료되었습니다. 품질 검증이 필요합니다.",
                )
            else:
                # Auto-approved → REPORTING. Dispatch report generation via outbox.
                _add_notification(
                    db,
                    request,
                    "COMPUTING_COMPLETE",
                    "AI 분석 완료",
                    "분석이 완료되어 보고서 생성 단계로 이동합니다.",
                )

        db.add(
            OutboxEvent(
                event_type="RUN_COMPLETED",
                aggregate_type="request",
                aggregate_id=request.id,
                payload={
                    "request_id": str(request.id),
                    "run_id": str(run.id),
                    "request_status": request.status,
                },
            )
        )

    logger.info(
        "Run %s result reported: %s (request %s → %s)",
        run_id,
        payload.status,
        run.request_id,
        request.status,
    )

    return RunResultResponse(
        run_id=str(run.id),
        request_id=str(request.id),
        request_status=request.status,
    )


# ---------------------------------------------------------------------------
# POST /internal/runs/{run_id}/heartbeat
# ---------------------------------------------------------------------------
@router.post(
    "/runs/{run_id}/heartbeat",
    response_model=HeartbeatResponse,
    dependencies=[Depends(verify_internal_key)],
)
async def report_heartbeat(
    run_id: uuid.UUID,
    payload: HeartbeatPayload,
    db: AsyncSession = Depends(get_db),
) -> HeartbeatResponse:
    """Worker sends periodic heartbeat to signal liveness."""
    run = (
        await db.execute(select(Run).where(Run.id == run_id))
    ).scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    run.heartbeat_at = datetime.now(timezone.utc)
    if payload.worker_id:
        run.worker_id = payload.worker_id

    # Store progress in job_spec metadata (non-destructive)
    if payload.progress_pct is not None or payload.current_step is not None:
        progress = (run.job_spec or {}).get("_progress", {})
        if payload.progress_pct is not None:
            progress["pct"] = payload.progress_pct
        if payload.current_step is not None:
            progress["current_step"] = payload.current_step
        job_spec = dict(run.job_spec or {})
        job_spec["_progress"] = progress
        run.job_spec = job_spec

    logger.debug("Heartbeat for run %s from worker %s", run_id, payload.worker_id)

    return HeartbeatResponse(run_id=str(run.id))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _add_notification(
    db: AsyncSession,
    request: Request,
    event_type: str,
    title: str,
    body: str,
) -> None:
    """Add a notification for the request owner (best-effort)."""
    if not request.requested_by:
        return
    db.add(
        Notification(
            institution_id=request.institution_id,
            user_id=request.requested_by,
            event_type=event_type,
            title=title,
            body=body,
            entity_type="request",
            entity_id=request.id,
            metadata_={},
        )
    )
