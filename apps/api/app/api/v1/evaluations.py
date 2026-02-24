"""Evaluation endpoints for human-in-the-loop review workflow."""

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.dependencies import AuthenticatedUser, DbSession
from app.models.evaluation import Evaluation, ServiceEvaluator
from app.models.outbox import OutboxEvent
from app.models.request import Case, CaseFile, Request
from app.models.run import Run
from app.schemas.evaluation import (
    EvaluationCreate,
    EvaluationDetailResponse,
    EvaluationQueueItem,
    EvaluationQueueResponse,
    EvaluationRead,
)
from app.services.notification_service import create_notification

router = APIRouter(tags=["Evaluations"])


@router.get("/evaluations/queue", response_model=EvaluationQueueResponse)
async def list_evaluation_queue(
    db: DbSession,
    user: AuthenticatedUser,
):
    """List requests in QC status where current user is an active evaluator."""
    # Find services where user is active evaluator
    eval_result = await db.execute(
        select(ServiceEvaluator.service_id).where(
            ServiceEvaluator.user_id == user.id,
            ServiceEvaluator.is_active.is_(True),
            ServiceEvaluator.institution_id == user.institution_id,
        )
    )
    service_ids = [row[0] for row in eval_result.all()]

    if not service_ids:
        return EvaluationQueueResponse(items=[])

    # Find requests in QC status for those services
    req_result = await db.execute(
        select(Request)
        .where(
            Request.service_id.in_(service_ids),
            Request.status == "QC",
            Request.institution_id == user.institution_id,
        )
        .order_by(Request.created_at.asc())
        .limit(100)
    )
    requests = req_result.scalars().all()

    items = []
    for req in requests:
        snapshot = req.service_snapshot or {}
        items.append(
            EvaluationQueueItem(
                request_id=req.id,
                request_status=req.status,
                service_name=snapshot.get("name", ""),
                service_display_name=snapshot.get("display_name", ""),
                case_count=len(req.cases) if req.cases else 0,
                created_at=req.created_at,
                priority=str(req.priority) if req.priority is not None else "NORMAL",
            )
        )

    return EvaluationQueueResponse(items=items)


@router.get("/evaluations/{request_id}", response_model=EvaluationDetailResponse)
async def get_evaluation_detail(
    request_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Full evaluation context: cases, files, runs, previous evaluations."""
    req = await db.execute(
        select(Request).where(
            Request.id == request_id,
            Request.institution_id == user.institution_id,
        )
    )
    request = req.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Cases
    cases_result = await db.execute(
        select(Case).where(Case.request_id == request_id)
    )
    cases = cases_result.scalars().all()

    # Files
    case_ids = [c.id for c in cases]
    files = []
    if case_ids:
        files_result = await db.execute(
            select(CaseFile).where(CaseFile.case_id.in_(case_ids))
        )
        files = files_result.scalars().all()

    # Runs
    runs_result = await db.execute(
        select(Run).where(Run.request_id == request_id)
    )
    runs = runs_result.scalars().all()

    # Previous evaluations
    evals_result = await db.execute(
        select(Evaluation)
        .where(Evaluation.request_id == request_id)
        .order_by(Evaluation.created_at.desc())
    )
    evaluations = evals_result.scalars().all()

    snapshot = request.service_snapshot or {}
    return EvaluationDetailResponse(
        request_id=request.id,
        request_status=request.status,
        service_name=snapshot.get("name", ""),
        service_display_name=snapshot.get("display_name", ""),
        cases=[
            {
                "id": str(c.id),
                "patient_ref": c.patient_ref,
                "status": c.status,
                "demographics": c.demographics,
            }
            for c in cases
        ],
        files=[
            {
                "id": str(f.id),
                "case_id": str(f.case_id),
                "slot": f.slot,
                "filename": f.filename,
                "file_size": f.file_size,
                "storage_path": f.storage_path,
                "status": f.status,
            }
            for f in files
        ],
        runs=[
            {
                "id": str(r.id),
                "status": r.status,
                "result_manifest": r.result_manifest,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ],
        evaluations=[
            EvaluationRead(
                id=e.id,
                institution_id=e.institution_id,
                request_id=e.request_id,
                run_id=e.run_id,
                evaluator_id=e.evaluator_id,
                decision=e.decision,
                comments=e.comments,
                watermark_text=e.watermark_text,
                output_storage_path=e.output_storage_path,
                created_at=e.created_at,
            )
            for e in evaluations
        ],
    )


@router.post("/evaluations/{request_id}/decide", response_model=EvaluationRead)
async def submit_evaluation(
    request_id: uuid.UUID,
    body: EvaluationCreate,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Submit evaluation decision: APPROVE, REJECT, or REVISION_NEEDED."""
    # Load request with FOR UPDATE
    req_result = await db.execute(
        select(Request)
        .where(
            Request.id == request_id,
            Request.institution_id == user.institution_id,
        )
        .with_for_update()
    )
    request = req_result.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != "QC":
        raise HTTPException(status_code=409, detail="Request is not in QC status")

    # Verify user is assigned evaluator for this service
    eval_check = await db.execute(
        select(ServiceEvaluator).where(
            ServiceEvaluator.service_id == request.service_id,
            ServiceEvaluator.user_id == user.id,
            ServiceEvaluator.is_active.is_(True),
        )
    )
    if not eval_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not assigned as evaluator for this service")

    # Create evaluation record
    evaluation = Evaluation(
        institution_id=user.institution_id,
        request_id=request_id,
        evaluator_id=user.id,
        decision=body.decision,
        comments=body.comments,
        watermark_text=body.watermark_text,
    )
    db.add(evaluation)
    await db.flush()

    if body.decision == "APPROVE":
        # Emit watermark event, transition to REPORTING
        request.status = "REPORTING"
        db.add(
            OutboxEvent(
                event_type="WATERMARK_REQUESTED",
                aggregate_type="request",
                aggregate_id=request.id,
                payload={
                    "request_id": str(request.id),
                    "evaluation_id": str(evaluation.id),
                    "watermark_text": body.watermark_text or "",
                },
            )
        )
        await create_notification(
            db,
            institution_id=request.institution_id,
            user_id=request.requested_by,
            event_type="EVALUATION_APPROVED",
            title="평가 완료 — 워터마크 처리 중",
            body="전문가 평가가 승인되었습니다. 워터마크 처리가 진행됩니다.",
            entity_type="request",
            entity_id=request.id,
            metadata={"status": "REPORTING"},
        )

    elif body.decision == "REJECT":
        request.status = "FAILED"
        request.cancel_reason = f"평가자 반려: {body.comments or '사유 없음'}"
        await create_notification(
            db,
            institution_id=request.institution_id,
            user_id=request.requested_by,
            event_type="EVALUATION_REJECTED",
            title="평가 결과: 반려됨",
            body=body.comments or "전문가 평가에서 반려되었습니다.",
            entity_type="request",
            entity_id=request.id,
            metadata={"status": "FAILED"},
        )

    elif body.decision == "REVISION_NEEDED":
        request.status = "COMPUTING"
        await create_notification(
            db,
            institution_id=request.institution_id,
            user_id=request.requested_by,
            event_type="EVALUATION_REVISION",
            title="수정 요청이 접수되었습니다",
            body=body.comments or "전문가가 수정을 요청했습니다. 재분석이 진행됩니다.",
            entity_type="request",
            entity_id=request.id,
            metadata={"status": "COMPUTING"},
        )

    await db.flush()
    await db.refresh(evaluation)
    return EvaluationRead(
        id=evaluation.id,
        institution_id=evaluation.institution_id,
        request_id=evaluation.request_id,
        run_id=evaluation.run_id,
        evaluator_id=evaluation.evaluator_id,
        decision=evaluation.decision,
        comments=evaluation.comments,
        watermark_text=evaluation.watermark_text,
        output_storage_path=evaluation.output_storage_path,
        created_at=evaluation.created_at,
    )
