import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.qc_decision import QCDecision
from app.models.report import Report, ReportReview
from app.models.request import Case, Request
from app.models.run import Run, RunStep
from app.schemas.review import (
    QCDecisionCreate,
    ReportReviewCreate,
    ReviewDetail,
    ReviewQueueItem,
    ReviewQueueResponse,
)
from app.schemas.request import RequestRead
from app.services.state_machine import RequestStatus as SMStatus
from app.services.state_machine import validate_transition

router = APIRouter(prefix="/reviews", tags=["Reviews"])

_require_expert = require_roles("REVIEWER", "SYSTEM_ADMIN")


def _request_to_queue_item(req: Request) -> ReviewQueueItem:
    service_snapshot = req.service_snapshot or {}
    return ReviewQueueItem(
        id=req.id,
        service_name=service_snapshot.get("name"),
        service_display_name=service_snapshot.get("display_name"),
        status=req.status,
        case_count=len(req.cases) if req.cases else 0,
        priority=req.priority,
        requested_by=req.requested_by,
        institution_id=req.institution_id,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


@router.get("/queue", response_model=ReviewQueueResponse)
async def list_review_queue(
    db: DbSession,
    user: CurrentUser = Depends(_require_expert),
    status_filter: str | None = Query(default=None, alias="status"),
):
    review_statuses = ["QC", "EXPERT_REVIEW"]
    if status_filter and status_filter in review_statuses:
        review_statuses = [status_filter]

    query = (
        select(Request)
        .options(selectinload(Request.cases))
        .where(
            Request.institution_id == user.institution_id,
            Request.status.in_(review_statuses),
        )
        .order_by(Request.priority.desc(), Request.created_at.asc())
    )
    result = await db.execute(query)
    requests = result.scalars().all()

    completed_query = (
        select(Request)
        .options(selectinload(Request.cases))
        .where(
            Request.institution_id == user.institution_id,
            Request.status.in_(["REPORTING", "FINAL", "FAILED"]),
        )
        .order_by(Request.updated_at.desc())
        .limit(20)
    )

    if status_filter == "completed":
        result = await db.execute(completed_query)
        requests = result.scalars().all()

    items = [_request_to_queue_item(r) for r in requests]
    return ReviewQueueResponse(items=items, total=len(items))


@router.get("/{request_id}", response_model=ReviewDetail)
async def get_review_detail(request_id: uuid.UUID, db: DbSession, user: CurrentUser = Depends(_require_expert)):
    result = await db.execute(
        select(Request)
        .options(selectinload(Request.cases).selectinload(Case.files))
        .where(Request.id == request_id, Request.institution_id == user.institution_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    request_read = RequestRead(
        id=req.id,
        institution_id=req.institution_id,
        service_id=req.service_id,
        pipeline_id=req.pipeline_id,
        status=req.status,
        priority=req.priority,
        inputs=req.inputs,
        options=req.options,
        requested_by=req.requested_by,
        department=req.department,
        error_detail=req.error_detail,
        cancel_reason=req.cancel_reason,
        idempotency_key=req.idempotency_key,
        service_snapshot=req.service_snapshot,
        pipeline_snapshot=req.pipeline_snapshot,
        case_count=len(req.cases) if req.cases else 0,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )

    cases_data = [
        {"id": str(c.id), "patient_ref": c.patient_ref, "status": c.status, "demographics": c.demographics}
        for c in (req.cases or [])
    ]

    runs_result = await db.execute(
        select(Run).options(selectinload(Run.steps)).where(Run.request_id == request_id)
        .order_by(Run.created_at.desc())
    )
    runs = runs_result.scalars().all()
    runs_data = [
        {
            "id": str(r.id),
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "steps": [
                {"name": s.step_name, "status": s.status, "image": s.docker_image}
                for s in (r.steps or [])
            ],
        }
        for r in runs
    ]

    reports_result = await db.execute(
        select(Report).where(Report.request_id == request_id).order_by(Report.created_at.desc())
    )
    reports = reports_result.scalars().all()
    reports_data = [
        {
            "id": str(r.id),
            "status": r.status,
            "title": r.title,
            "summary": r.summary,
            "storage_path": r.pdf_storage_path,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]

    qc_result = await db.execute(
        select(QCDecision).where(QCDecision.request_id == request_id).order_by(QCDecision.created_at.desc())
    )
    qc_decisions = qc_result.scalars().all()
    qc_data = [
        {
            "id": str(q.id),
            "decision": q.decision,
            "qc_score": q.qc_score,
            "comments": q.comments,
            "reviewer_id": str(q.reviewer_id) if q.reviewer_id else None,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        }
        for q in qc_decisions
    ]

    review_result = await db.execute(
        select(ReportReview).where(ReportReview.report_id.in_([r.id for r in reports]))
        .order_by(ReportReview.created_at.desc())
    ) if reports else None
    review_data = []
    if review_result:
        reviews = review_result.scalars().all()
        review_data = [
            {
                "id": str(rv.id),
                "decision": rv.decision,
                "comments": rv.comments,
                "reviewer_id": str(rv.reviewer_id) if rv.reviewer_id else None,
                "created_at": rv.created_at.isoformat() if rv.created_at else None,
            }
            for rv in reviews
        ]

    return ReviewDetail(
        request=request_read,
        cases=cases_data,
        runs=runs_data,
        reports=reports_data,
        qc_decisions=qc_data,
        report_reviews=review_data,
    )


@router.post("/{request_id}/qc-decision", status_code=status.HTTP_200_OK)
async def submit_qc_decision(
    request_id: uuid.UUID,
    body: QCDecisionCreate,
    db: DbSession,
    user: CurrentUser = Depends(_require_expert),
):
    result = await db.execute(
        select(Request)
        .where(Request.id == request_id, Request.institution_id == user.institution_id)
        .with_for_update()
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.status != "QC":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request is not in QC status")

    qc = QCDecision(
        institution_id=user.institution_id,
        request_id=req.id,
        reviewer_id=user.id,
        decision=body.decision,
        qc_score=body.qc_score,
        comments=body.comments,
    )
    db.add(qc)

    if body.decision == "APPROVE":
        from_state = SMStatus(req.status)
        to_state = SMStatus.REPORTING
        validate_transition(from_state, to_state, user)
        req.status = to_state.value
    elif body.decision == "REJECT":
        req.status = "FAILED"
        req.error_detail = body.comments or "QC rejected"
    elif body.decision == "RERUN":
        req.status = "COMPUTING"

    await db.flush()
    return {"status": req.status, "decision": body.decision}


@router.post("/{request_id}/report-review", status_code=status.HTTP_200_OK)
async def submit_report_review(
    request_id: uuid.UUID,
    body: ReportReviewCreate,
    db: DbSession,
    user: CurrentUser = Depends(_require_expert),
):
    result = await db.execute(
        select(Request)
        .where(Request.id == request_id, Request.institution_id == user.institution_id)
        .with_for_update()
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.status != "EXPERT_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request is not in EXPERT_REVIEW status",
        )

    report_result = await db.execute(
        select(Report).where(Report.request_id == request_id).order_by(Report.created_at.desc()).limit(1)
    )
    report = report_result.scalar_one_or_none()

    if report:
        review = ReportReview(
            report_id=report.id,
            reviewer_id=user.id,
            decision=body.decision,
            comments=body.comments,
        )
        db.add(review)

    if body.decision == "APPROVE":
        from_state = SMStatus(req.status)
        to_state = SMStatus.FINAL
        validate_transition(from_state, to_state, user)
        req.status = to_state.value
    elif body.decision == "REVISION_NEEDED":
        req.status = "COMPUTING"

    await db.flush()
    return {"status": req.status, "decision": body.decision}
