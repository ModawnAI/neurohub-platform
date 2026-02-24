"""Review endpoints: QC decisions, expert reviews, assignments, consensus, and PDF reports."""

import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi import Request as FastAPIRequest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.audit import PatientAccessLog
from app.models.outbox import OutboxEvent
from app.models.qc_decision import QCDecision
from app.models.report import Report, ReportReview, ReviewAssignment
from app.models.request import Case, Request
from app.models.run import Run
from app.schemas.request import RequestRead
from app.schemas.review import (
    QCDecisionCreate,
    ReportReviewCreate,
    ReviewAssignmentCreate,
    ReviewAssignmentRead,
    ReviewDetail,
    ReviewQueueItem,
    ReviewQueueResponse,
)
from app.services.notification_service import create_notification
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
async def get_review_detail(
    request_id: uuid.UUID,
    http_request: FastAPIRequest,
    db: DbSession,
    user: CurrentUser = Depends(_require_expert),
):
    result = await db.execute(
        select(Request)
        .options(selectinload(Request.cases).selectinload(Case.files))
        .where(Request.id == request_id, Request.institution_id == user.institution_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    # Log patient data access for audit compliance
    client_ip = http_request.client.host if http_request.client else None
    for case in req.cases:
        if case.patient_ref:
            db.add(
                PatientAccessLog(
                    institution_id=user.institution_id,
                    user_id=user.id,
                    patient_ref=case.patient_ref,
                    access_type="REVIEW",
                    resource_type="request",
                    resource_id=req.id,
                    ip_address=client_ip,
                )
            )

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
        {
            "id": str(c.id),
            "patient_ref": c.patient_ref,
            "status": c.status,
            "demographics": c.demographics,
        }
        for c in (req.cases or [])
    ]

    runs_result = await db.execute(
        select(Run)
        .options(selectinload(Run.steps))
        .where(Run.request_id == request_id)
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
        select(QCDecision)
        .where(QCDecision.request_id == request_id)
        .order_by(QCDecision.created_at.desc())
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

    review_result = (
        await db.execute(
            select(ReportReview)
            .where(ReportReview.report_id.in_([r.id for r in reports]))
            .order_by(ReportReview.created_at.desc())
        )
        if reports
        else None
    )
    review_data = []
    if review_result:
        reviews = review_result.scalars().all()
        review_data = [
            {
                "id": str(rv.id),
                "decision": rv.decision,
                "comments": rv.comments,
                "severity": rv.severity,
                "category": rv.category,
                "recommendation": rv.recommendation,
                "findings": rv.findings,
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


# ── Review Assignment ─────────────────────────────────────────────────────


@router.post("/{request_id}/assign", response_model=ReviewAssignmentRead)
async def assign_reviewer(
    request_id: uuid.UUID,
    body: ReviewAssignmentCreate,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """Assign a reviewer to a request in EXPERT_REVIEW state."""
    result = await db.execute(
        select(Request).where(
            Request.id == request_id,
            Request.institution_id == user.institution_id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.status != "EXPERT_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request must be in EXPERT_REVIEW status to assign reviewers",
        )

    # Prevent duplicate assignment
    existing = await db.execute(
        select(ReviewAssignment).where(
            ReviewAssignment.request_id == request_id,
            ReviewAssignment.reviewer_id == body.reviewer_id,
            ReviewAssignment.status == "PENDING",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Reviewer already assigned"
        )

    assignment = ReviewAssignment(
        request_id=request_id,
        reviewer_id=body.reviewer_id,
        assigned_by=user.id,
    )
    db.add(assignment)

    # Notify the assigned reviewer
    await create_notification(
        db,
        institution_id=req.institution_id,
        user_id=body.reviewer_id,
        event_type="REVIEW_ASSIGNED",
        title="검토 요청이 배정되었습니다",
        body=f"요청 {str(request_id)[:8]}...에 대한 전문가 검토가 배정되었습니다.",
        entity_type="request",
        entity_id=request_id,
        metadata={"assigned_by": str(user.id)},
    )

    await db.flush()
    return ReviewAssignmentRead.model_validate(assignment)


@router.get("/{request_id}/assignments", response_model=list[ReviewAssignmentRead])
async def list_assignments(
    request_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(_require_expert),
):
    """List all reviewer assignments for a request."""
    result = await db.execute(
        select(ReviewAssignment)
        .where(ReviewAssignment.request_id == request_id)
        .order_by(ReviewAssignment.assigned_at.desc())
    )
    return [ReviewAssignmentRead.model_validate(a) for a in result.scalars().all()]


# ── QC Decision ───────────────────────────────────────────────────────────


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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request is not in QC status",
        )

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

    # Outbox event for audit trail
    db.add(
        OutboxEvent(
            event_type=f"QC_{body.decision}",
            aggregate_type="request",
            aggregate_id=req.id,
            payload={
                "request_id": str(req.id),
                "decision": body.decision,
                "reviewer_id": str(user.id),
                "qc_score": body.qc_score,
            },
        )
    )

    # Notify the request owner about the QC decision
    decision_labels = {"APPROVE": "승인", "REJECT": "거절", "RERUN": "재분석"}
    if req.requested_by:
        await create_notification(
            db,
            institution_id=req.institution_id,
            user_id=req.requested_by,
            event_type=f"QC_{body.decision}",
            title=f"QC 결정: {decision_labels.get(body.decision, body.decision)}",
            body=body.comments,
            entity_type="request",
            entity_id=req.id,
            metadata={"status": req.status, "decision": body.decision},
        )

    await db.flush()
    return {"status": req.status, "decision": body.decision}


# ── Expert Report Review (with structured findings + consensus) ───────────


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
        select(Report)
        .where(Report.request_id == request_id)
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    report = report_result.scalar_one_or_none()

    if report:
        review = ReportReview(
            report_id=report.id,
            reviewer_id=user.id,
            decision=body.decision,
            comments=body.comments,
            severity=body.severity,
            category=body.category,
            recommendation=body.recommendation,
            findings=body.findings,
        )
        db.add(review)

    # Mark assignment as completed if exists
    assignment_result = await db.execute(
        select(ReviewAssignment).where(
            ReviewAssignment.request_id == request_id,
            ReviewAssignment.reviewer_id == user.id,
            ReviewAssignment.status == "PENDING",
        )
    )
    assignment = assignment_result.scalar_one_or_none()
    if assignment:
        from datetime import datetime, timezone

        assignment.status = "COMPLETED"
        assignment.completed_at = datetime.now(timezone.utc)

    # Multi-reviewer consensus: check if all assigned reviewers have submitted
    consensus_decision = await _check_consensus(db, request_id, body.decision)

    if consensus_decision == "APPROVE":
        from_state = SMStatus(req.status)
        to_state = SMStatus.FINAL
        validate_transition(from_state, to_state, user)
        req.status = to_state.value
    elif consensus_decision == "REVISION_NEEDED":
        req.status = "COMPUTING"
    # If consensus_decision is None, waiting for more reviews — don't transition

    # Outbox event for audit trail
    db.add(
        OutboxEvent(
            event_type=f"REPORT_REVIEW_{body.decision}",
            aggregate_type="request",
            aggregate_id=req.id,
            payload={
                "request_id": str(req.id),
                "decision": body.decision,
                "reviewer_id": str(user.id),
                "severity": body.severity,
                "category": body.category,
                "consensus": consensus_decision,
            },
        )
    )

    # Notify the request owner
    review_labels = {"APPROVE": "최종 승인", "REVISION_NEEDED": "수정 필요"}
    if req.requested_by:
        await create_notification(
            db,
            institution_id=req.institution_id,
            user_id=req.requested_by,
            event_type=f"REPORT_REVIEW_{body.decision}",
            title=f"보고서 검토: {review_labels.get(body.decision, body.decision)}",
            body=body.comments,
            entity_type="request",
            entity_id=req.id,
            metadata={
                "status": req.status,
                "decision": body.decision,
                "consensus": consensus_decision,
            },
        )

    await db.flush()
    return {
        "status": req.status,
        "decision": body.decision,
        "consensus": consensus_decision,
    }


async def _check_consensus(
    db: DbSession,
    request_id: uuid.UUID,
    current_decision: str,
) -> str | None:
    """Check multi-reviewer consensus. Returns decision if consensus reached, None otherwise.

    Rules:
    - If no assignments exist, the single review is the consensus (immediate).
    - If assignments exist, wait until all assigned reviewers submit.
    - Majority vote wins. Ties default to REVISION_NEEDED (conservative).
    """
    assignments_result = await db.execute(
        select(ReviewAssignment).where(ReviewAssignment.request_id == request_id)
    )
    assignments = assignments_result.scalars().all()

    if not assignments:
        # No formal assignments — single reviewer decides
        return current_decision

    # Check if all assignments are completed
    pending = [a for a in assignments if a.status == "PENDING"]
    if pending:
        return None  # Still waiting for more reviews

    # All reviewers submitted — compute majority
    completed = [a for a in assignments if a.status == "COMPLETED"]
    if not completed:
        return current_decision

    # Get all reviews for the latest report
    report_result = await db.execute(
        select(Report)
        .where(Report.request_id == request_id)
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    report = report_result.scalar_one_or_none()
    if not report:
        return current_decision

    reviews_result = await db.execute(
        select(ReportReview).where(ReportReview.report_id == report.id)
    )
    reviews = reviews_result.scalars().all()

    if not reviews:
        return current_decision

    votes = Counter(r.decision for r in reviews)
    approve_count = votes.get("APPROVE", 0)
    revision_count = votes.get("REVISION_NEEDED", 0)

    if approve_count > revision_count:
        return "APPROVE"
    return "REVISION_NEEDED"


# ── Review History / Audit Trail ──────────────────────────────────────────


@router.get("/{request_id}/history")
async def get_review_history(
    request_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(_require_expert),
):
    """Get complete review audit trail for a request."""
    # Verify access
    result = await db.execute(
        select(Request).where(
            Request.id == request_id,
            Request.institution_id == user.institution_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    # QC decisions
    qc_result = await db.execute(
        select(QCDecision)
        .where(QCDecision.request_id == request_id)
        .order_by(QCDecision.created_at.asc())
    )
    qc_decisions = [
        {
            "type": "qc_decision",
            "id": str(q.id),
            "decision": q.decision,
            "qc_score": q.qc_score,
            "comments": q.comments,
            "reviewer_id": str(q.reviewer_id) if q.reviewer_id else None,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        }
        for q in qc_result.scalars().all()
    ]

    # Report reviews
    reports_result = await db.execute(select(Report).where(Report.request_id == request_id))
    report_ids = [r.id for r in reports_result.scalars().all()]

    report_reviews = []
    if report_ids:
        rv_result = await db.execute(
            select(ReportReview)
            .where(ReportReview.report_id.in_(report_ids))
            .order_by(ReportReview.created_at.asc())
        )
        report_reviews = [
            {
                "type": "report_review",
                "id": str(rv.id),
                "decision": rv.decision,
                "comments": rv.comments,
                "severity": rv.severity,
                "category": rv.category,
                "recommendation": rv.recommendation,
                "reviewer_id": str(rv.reviewer_id) if rv.reviewer_id else None,
                "created_at": rv.created_at.isoformat() if rv.created_at else None,
            }
            for rv in rv_result.scalars().all()
        ]

    # Assignments
    assign_result = await db.execute(
        select(ReviewAssignment)
        .where(ReviewAssignment.request_id == request_id)
        .order_by(ReviewAssignment.assigned_at.asc())
    )
    assignments = [
        {
            "type": "assignment",
            "id": str(a.id),
            "reviewer_id": str(a.reviewer_id),
            "assigned_by": str(a.assigned_by) if a.assigned_by else None,
            "status": a.status,
            "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        }
        for a in assign_result.scalars().all()
    ]

    # Merge and sort by time
    all_events = qc_decisions + report_reviews + assignments
    all_events.sort(key=lambda e: e.get("created_at") or e.get("assigned_at") or "")

    return {"request_id": str(request_id), "events": all_events, "total": len(all_events)}


# ── PDF Report Generation ─────────────────────────────────────────────────


@router.post("/{request_id}/generate-pdf", status_code=status.HTTP_202_ACCEPTED)
async def trigger_pdf_generation(
    request_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(_require_expert),
):
    """Trigger async PDF report generation via Celery."""
    result = await db.execute(
        select(Request).where(
            Request.id == request_id,
            Request.institution_id == user.institution_id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    # Must have a report record
    report_result = await db.execute(select(Report).where(Report.request_id == request_id).limit(1))
    if not report_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No report record exists for this request",
        )

    from app.worker.celery_app import celery_app

    task = celery_app.send_task(
        "neurohub.tasks.generate_pdf_report",
        args=[str(request_id)],
        queue="reporting",
    )

    return {"task_id": task.id, "status": "QUEUED"}


@router.get("/{request_id}/report-pdf")
async def download_report_pdf(
    request_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(_require_expert),
):
    """Get presigned download URL for the PDF report."""
    result = await db.execute(
        select(Request).where(
            Request.id == request_id,
            Request.institution_id == user.institution_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    report_result = await db.execute(
        select(Report)
        .where(Report.request_id == request_id)
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    report = report_result.scalar_one_or_none()
    if not report or not report.pdf_storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF report not yet generated",
        )

    from app.services.storage import create_presigned_download

    # storage_path format: "bucket/path/to/file.pdf"
    parts = report.pdf_storage_path.split("/", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=500, detail="Invalid storage path")
    bucket, path = parts

    url = await create_presigned_download(bucket, path)
    return {"download_url": url, "report_id": str(report.id)}
