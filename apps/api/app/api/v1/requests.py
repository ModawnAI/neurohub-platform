import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from fastapi import Request as FastAPIRequest
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.dependencies import AuthenticatedUser, DbSession
from app.models.audit import AuditLog, PatientAccessLog
from app.models.idempotency import IdempotencyKey
from app.models.outbox import OutboxEvent
from app.models.request import Case, Request
from app.models.run import Run, RunStep
from app.models.service import PipelineDefinition, ServiceDefinition
from app.schemas.pagination import PaginatedResponse
from app.schemas.request import (
    CancelRequest,
    CaseReadBrief,
    ConfirmRequest,
    ReportSummary,
    RequestCreate,
    RequestRead,
    RequestStatus,
    TransitionRequest,
)
from app.services.notification_service import create_notification
from app.services.state_machine import RequestStatus as SMStatus
from app.services.state_machine import validate_transition

router = APIRouter(tags=["Requests"])

IDEMPOTENCY_SCOPE_UI_REQUEST = "UI_REQUEST"
IDEMPOTENCY_TTL_HOURS = 24


def _client_ip(req: FastAPIRequest) -> str | None:
    return req.client.host if req.client else None


def _canonical_payload_hash(body: RequestCreate) -> str:
    payload = body.model_dump(mode="json", exclude={"idempotency_key"})
    canonical_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _to_read(req: Request, report=None) -> RequestRead:
    report_summary = None
    if report:
        report_summary = ReportSummary(
            id=report.id,
            status=report.status,
            title=report.title,
            summary=report.summary,
            conclusions=report.content.get("conclusions") if isinstance(report.content, dict) else None,
            generated_at=report.generated_at,
            pdf_storage_path=report.pdf_storage_path,
            watermarked_storage_path=report.watermarked_storage_path,
        )
    return RequestRead(
        id=req.id,
        institution_id=req.institution_id,
        service_id=req.service_id,
        pipeline_id=req.pipeline_id,
        status=RequestStatus(req.status),
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
        case_count=len(req.cases),
        cases=[
            CaseReadBrief(id=c.id, patient_ref=c.patient_ref, status=c.status)
            for c in req.cases
        ] if req.cases else None,
        report=report_summary,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


async def _load_request_or_404(
    db: DbSession,
    request_id: uuid.UUID,
    institution_id: uuid.UUID,
    for_update: bool = False,
) -> Request:
    query = select(Request).where(
        Request.id == request_id,
        Request.institution_id == institution_id,
    )
    if for_update:
        query = query.with_for_update()

    result = await db.execute(query)
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


async def _load_existing_by_idempotency(
    db: DbSession,
    institution_id: uuid.UUID,
    idempotency_key: str,
    payload_hash: str,
) -> Request | None:
    idem_result = await db.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.scope == IDEMPOTENCY_SCOPE_UI_REQUEST,
            IdempotencyKey.idempotency_key == idempotency_key,
        )
    )
    idem = idem_result.scalar_one_or_none()
    if not idem:
        return None

    if idem.request_hash != payload_hash:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "IDEMPOTENCY_CONFLICT",
                "message": "Same idempotency key was used with different payload.",
                "idempotency_key": idempotency_key,
            },
        )

    if idem.resource_type != "request" or not idem.resource_id:
        return None

    try:
        request_id = uuid.UUID(idem.resource_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=409, detail="Invalid idempotency resource reference"
        ) from exc

    return await _load_request_or_404(db, request_id, institution_id)


async def _log_patient_access(
    db: DbSession,
    user_id: uuid.UUID,
    institution_id: uuid.UUID,
    patient_ref: str,
    access_type: str,
    resource_type: str,
    resource_id: uuid.UUID,
    ip: str | None,
) -> None:
    db.add(
        PatientAccessLog(
            institution_id=institution_id,
            user_id=user_id,
            patient_ref=patient_ref,
            access_type=access_type,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip,
        )
    )


def _add_audit(
    db: DbSession,
    user_id: uuid.UUID | None,
    institution_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    before_state: dict | None,
    after_state: dict | None,
    ip: str | None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            institution_id=institution_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip,
        )
    )


async def _notify_request_owner(
    db: DbSession,
    req: Request,
    event_type: str,
    title: str,
    body: str | None = None,
) -> None:
    """Send a notification to the request owner about a status change."""
    if not req.requested_by:
        return
    await create_notification(
        db,
        institution_id=req.institution_id,
        user_id=req.requested_by,
        event_type=event_type,
        title=title,
        body=body,
        entity_type="request",
        entity_id=req.id,
        metadata={"status": req.status},
    )


def _add_outbox(
    db: DbSession,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    payload: dict,
) -> None:
    db.add(
        OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
        )
    )


@router.post("/requests", response_model=RequestRead, status_code=status.HTTP_201_CREATED)
async def create_request(
    body: RequestCreate,
    db: DbSession,
    user: AuthenticatedUser,
    http_request: FastAPIRequest,
):
    payload_hash: str | None = None
    idempotency_record: IdempotencyKey | None = None

    if body.idempotency_key:
        payload_hash = _canonical_payload_hash(body)
        existing = await _load_existing_by_idempotency(
            db=db,
            institution_id=user.institution_id,
            idempotency_key=body.idempotency_key,
            payload_hash=payload_hash,
        )
        if existing:
            read = _to_read(existing)
            return JSONResponse(
                status_code=200,
                content=read.model_dump(mode="json"),
            )

        idempotency_record = IdempotencyKey(
            scope=IDEMPOTENCY_SCOPE_UI_REQUEST,
            idempotency_key=body.idempotency_key,
            request_hash=payload_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=IDEMPOTENCY_TTL_HOURS),
        )
        db.add(idempotency_record)

    from sqlalchemy import or_

    svc_result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == body.service_id,
            or_(
                ServiceDefinition.institution_id == user.institution_id,
                ServiceDefinition.status == "PUBLISHED",
            ),
        )
    )
    service = svc_result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    pipe_result = await db.execute(
        select(PipelineDefinition).where(
            PipelineDefinition.id == body.pipeline_id,
            PipelineDefinition.service_id == service.id,
        )
    )
    pipeline = pipe_result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    req = Request(
        institution_id=user.institution_id,
        service_id=service.id,
        pipeline_id=pipeline.id,
        status=SMStatus.CREATED.value,
        priority=body.priority,
        inputs=body.inputs,
        options=body.options,
        requested_by=user.id,
        service_snapshot={
            "name": service.name,
            "display_name": service.display_name,
            "version": service.version,
        },
        pipeline_snapshot={
            "name": pipeline.name,
            "version": pipeline.version,
            "steps": pipeline.steps or [],
            "qc_rules": pipeline.qc_rules or {},
        },
        idempotency_key=body.idempotency_key,
    )
    db.add(req)
    await db.flush()

    for case_payload in body.cases:
        db.add(
            Case(
                institution_id=user.institution_id,
                request_id=req.id,
                patient_ref=case_payload.patient_ref,
                demographics=case_payload.demographics,
                status="CREATED",
            )
        )

    _add_audit(
        db=db,
        user_id=user.id,
        institution_id=user.institution_id,
        action="CREATE_REQUEST",
        entity_type="request",
        entity_id=req.id,
        before_state=None,
        after_state={"status": req.status},
        ip=_client_ip(http_request),
    )
    await db.flush()
    await db.refresh(req)
    response_payload = _to_read(req)

    if idempotency_record:
        idempotency_record.resource_type = "request"
        idempotency_record.resource_id = str(req.id)
        idempotency_record.response_status = 201
        idempotency_record.response_body = response_payload.model_dump(mode="json")
        await db.flush()

    return response_payload


@router.get("/requests", response_model=PaginatedResponse[RequestRead])
async def list_requests(
    db: DbSession,
    user: AuthenticatedUser,
    status_filter: RequestStatus | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    query = select(Request).where(Request.institution_id == user.institution_id)
    count_query = select(func.count(Request.id)).where(
        Request.institution_id == user.institution_id
    )

    if status_filter:
        query = query.where(Request.status == status_filter.value)
        count_query = count_query.where(Request.status == status_filter.value)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(query.order_by(Request.created_at.desc()).offset(offset).limit(limit))
    rows = result.scalars().all()
    return PaginatedResponse(
        items=[_to_read(r) for r in rows],
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + limit) < total,
    )


@router.get("/requests/{request_id}", response_model=RequestRead)
async def get_request(
    request_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
    http_request: FastAPIRequest,
):
    from app.models.report import Report

    req = await _load_request_or_404(db, request_id, user.institution_id)

    # Log patient data access for each case
    for case in req.cases:
        if case.patient_ref:
            await _log_patient_access(
                db=db,
                user_id=user.id,
                institution_id=user.institution_id,
                patient_ref=case.patient_ref,
                access_type="VIEW",
                resource_type="request",
                resource_id=req.id,
                ip=_client_ip(http_request),
            )

    # Fetch latest report for this request
    report_result = await db.execute(
        select(Report)
        .where(Report.request_id == request_id)
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    report = report_result.scalar_one_or_none()

    return _to_read(req, report=report)


@router.post("/requests/{request_id}/transition", response_model=RequestRead)
async def transition_request(
    request_id: uuid.UUID,
    body: TransitionRequest,
    db: DbSession,
    user: AuthenticatedUser,
    http_request: FastAPIRequest,
):
    """Generic state transition endpoint for advancing a request through the workflow."""
    req = await _load_request_or_404(db, request_id, user.institution_id, for_update=True)
    from_state = SMStatus(req.status)
    to_state = SMStatus(body.target_status.value)
    validate_transition(from_state, to_state, user)

    before = {"status": req.status}
    req.status = to_state.value

    # Auto-advance case statuses when transitioning to STAGING
    if to_state == SMStatus.STAGING:
        for case in req.cases:
            case.status = "READY"

    _add_audit(
        db=db,
        user_id=user.id,
        institution_id=user.institution_id,
        action=f"TRANSITION_{from_state.value}_TO_{to_state.value}",
        entity_type="request",
        entity_id=req.id,
        before_state=before,
        after_state={"status": req.status, "note": body.note},
        ip=_client_ip(http_request),
    )
    await _notify_request_owner(
        db,
        req,
        event_type=f"REQUEST_{to_state.value}",
        title=f"요청 상태 변경: {to_state.value}",
        body=f"요청이 {from_state.value}에서 {to_state.value}(으)로 전환되었습니다.",
    )

    # Auto-trigger report generation when transitioning to REPORTING
    if to_state == SMStatus.REPORTING:
        _add_outbox(
            db=db,
            event_type="REPORT_REQUESTED",
            aggregate_type="request",
            aggregate_id=req.id,
            payload={"request_id": str(req.id)},
        )

    await db.flush()
    await db.refresh(req)
    return _to_read(req)


@router.post("/requests/{request_id}/confirm", response_model=RequestRead)
async def confirm_request(
    request_id: uuid.UUID,
    body: ConfirmRequest,
    db: DbSession,
    user: AuthenticatedUser,
    http_request: FastAPIRequest,
):
    req = await _load_request_or_404(db, request_id, user.institution_id, for_update=True)

    # Auto-advance through intermediate states to STAGING
    if req.status in (SMStatus.CREATED.value, SMStatus.RECEIVING.value):
        req.status = SMStatus.STAGING.value
        for case in req.cases:
            case.status = "READY"

    if req.status != SMStatus.STAGING.value:
        raise HTTPException(
            status_code=409,
            detail=f"Request must be STAGING to confirm. current={req.status}",
        )

    from_state = SMStatus(req.status)
    validate_transition(from_state, SMStatus.READY_TO_COMPUTE, user)

    if not req.cases or any(c.status != "READY" for c in req.cases):
        raise HTTPException(status_code=409, detail="All cases must be READY before confirm")

    before = {"status": req.status}
    req.status = SMStatus.READY_TO_COMPUTE.value
    _add_audit(
        db=db,
        user_id=user.id,
        institution_id=user.institution_id,
        action="CONFIRM_REQUEST",
        entity_type="request",
        entity_id=req.id,
        before_state=before,
        after_state={"status": req.status, "confirm_note": body.confirm_note},
        ip=_client_ip(http_request),
    )
    await _notify_request_owner(
        db,
        req,
        event_type="REQUEST_CONFIRMED",
        title="요청 확인 완료",
        body="요청이 확인되었습니다. 분석 제출이 가능합니다.",
    )
    await db.flush()
    await db.refresh(req)
    return _to_read(req)


@router.post("/requests/{request_id}/cancel", response_model=RequestRead)
async def cancel_request(
    request_id: uuid.UUID,
    body: CancelRequest,
    db: DbSession,
    user: AuthenticatedUser,
    http_request: FastAPIRequest,
):
    req = await _load_request_or_404(db, request_id, user.institution_id, for_update=True)
    from_state = SMStatus(req.status)
    validate_transition(from_state, SMStatus.CANCELLED, user)

    before = {"status": req.status}
    req.status = SMStatus.CANCELLED.value
    req.cancel_reason = body.reason

    _add_audit(
        db=db,
        user_id=user.id,
        institution_id=user.institution_id,
        action="CANCEL_REQUEST",
        entity_type="request",
        entity_id=req.id,
        before_state=before,
        after_state={"status": req.status, "reason": body.reason},
        ip=_client_ip(http_request),
    )
    await _notify_request_owner(
        db,
        req,
        event_type="REQUEST_CANCELLED",
        title="요청 취소됨",
        body=f"요청이 취소되었습니다. 사유: {body.reason or '없음'}",
    )
    await db.flush()
    await db.refresh(req)
    return _to_read(req)


@router.post("/requests/{request_id}/submit")
async def submit_request(
    request_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
    http_request: FastAPIRequest,
):
    req = await _load_request_or_404(db, request_id, user.institution_id, for_update=True)
    if req.status != SMStatus.READY_TO_COMPUTE.value:
        raise HTTPException(status_code=409, detail="Request must be READY_TO_COMPUTE")
    if req.runs:
        raise HTTPException(status_code=409, detail="Runs already exist for this request")

    from_state = SMStatus(req.status)
    validate_transition(from_state, SMStatus.COMPUTING, user)

    run_ids: list[str] = []
    for case in req.cases:
        run = Run(
            institution_id=req.institution_id,
            request_id=req.id,
            case_id=case.id,
            status="PENDING",
            priority=req.priority,
            job_spec={
                "run_id": None,
                "request_id": str(req.id),
                "case_id": str(case.id),
                "pipeline": req.pipeline_snapshot,
            },
        )
        db.add(run)
        await db.flush()
        run.job_spec = {
            "run_id": str(run.id),
            "request_id": str(req.id),
            "case_id": str(case.id),
            "pipeline": req.pipeline_snapshot,
        }
        run_ids.append(str(run.id))
        req.current_run_id = run.id

        steps = (req.pipeline_snapshot or {}).get("steps", [])
        for idx, step in enumerate(steps):
            db.add(
                RunStep(
                    run_id=run.id,
                    step_index=idx,
                    step_name=step.get("name", f"step-{idx}"),
                    status="PENDING",
                    docker_image=step.get("image"),
                )
            )

    before = {"status": req.status}
    req.status = SMStatus.COMPUTING.value

    _add_outbox(
        db=db,
        event_type="RUN_SUBMITTED",
        aggregate_type="request",
        aggregate_id=req.id,
        payload={"request_id": str(req.id), "run_ids": run_ids},
    )
    _add_audit(
        db=db,
        user_id=user.id,
        institution_id=user.institution_id,
        action="SUBMIT_REQUEST",
        entity_type="request",
        entity_id=req.id,
        before_state=before,
        after_state={"status": req.status, "run_ids": run_ids},
        ip=_client_ip(http_request),
    )
    await _notify_request_owner(
        db,
        req,
        event_type="REQUEST_COMPUTING",
        title="AI 분석 시작",
        body="요청이 제출되어 AI 분석이 시작되었습니다.",
    )
    await db.flush()
    return {"request_id": str(req.id), "status": req.status, "run_ids": run_ids}


# ---------------------------------------------------------------------------
# Execute endpoint — triggers technique container execution for a request
# ---------------------------------------------------------------------------


@router.post("/requests/{request_id}/execute")
async def execute_request(
    request_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
    http_request: FastAPIRequest,
):
    """Trigger technique container execution for all cases in a request.

    This endpoint:
    1. Validates the request is in READY_TO_COMPUTE (or STAGING/CREATED for convenience)
    2. Creates Run records with technique fan-out
    3. Transitions the request to COMPUTING
    4. Dispatches technique execution tasks via Celery (local Docker containers)

    Unlike /submit (which creates generic pipeline Run+RunStep records for
    Fly.io container execution), this endpoint uses the technique-based
    execution model with LocalContainerRunner.

    Roles: PHYSICIAN, TECHNICIAN, SYSTEM_ADMIN
    """
    from app.models.technique import ServiceTechniqueWeight, TechniqueModule

    req = await _load_request_or_404(db, request_id, user.institution_id, for_update=True)

    # Allow from CREATED, RECEIVING, STAGING, or READY_TO_COMPUTE
    allowed_from = {
        SMStatus.CREATED.value,
        SMStatus.RECEIVING.value,
        SMStatus.STAGING.value,
        SMStatus.READY_TO_COMPUTE.value,
    }
    if req.status not in allowed_from:
        raise HTTPException(
            status_code=409,
            detail=f"Request is in {req.status} — cannot execute. "
                   f"Allowed: {', '.join(sorted(allowed_from))}",
        )

    if not req.cases:
        raise HTTPException(status_code=409, detail="No cases found for this request")

    # Look up techniques for this service
    technique_result = await db.execute(
        select(ServiceTechniqueWeight, TechniqueModule)
        .join(TechniqueModule, ServiceTechniqueWeight.technique_module_id == TechniqueModule.id)
        .where(
            ServiceTechniqueWeight.service_id == req.service_id,
            TechniqueModule.status == "ACTIVE",
        )
        .order_by(ServiceTechniqueWeight.base_weight.desc())
    )
    techniques = technique_result.all()

    if not techniques:
        raise HTTPException(
            status_code=409,
            detail="No active techniques configured for this service",
        )

    # Create Runs and TechniqueRuns for each case
    from app.models.technique import TechniqueRun

    run_ids: list[str] = []
    technique_run_ids: list[str] = []

    for case in req.cases:
        run = Run(
            institution_id=req.institution_id,
            request_id=req.id,
            case_id=case.id,
            status="PENDING",
            priority=req.priority,
            job_spec={
                "run_id": None,
                "request_id": str(req.id),
                "case_id": str(case.id),
                "service_id": str(req.service_id),
                "pipeline": req.pipeline_snapshot,
                "execution_mode": "technique_containers",
            },
        )
        db.add(run)
        await db.flush()

        run.job_spec = {**run.job_spec, "run_id": str(run.id)}
        run_ids.append(str(run.id))
        req.current_run_id = run.id

        # Create TechniqueRun for each active technique
        for weight, technique in techniques:
            tr = TechniqueRun(
                run_id=run.id,
                technique_module_id=technique.id,
                technique_key=technique.key,
                status="PENDING",
                job_spec={
                    "docker_image": technique.docker_image,
                    "technique_key": technique.key,
                    "modality": technique.modality,
                    "base_weight": weight.base_weight,
                    "resource_requirements": technique.resource_requirements or {},
                },
            )
            db.add(tr)
            await db.flush()
            technique_run_ids.append(str(tr.id))

    # Transition to COMPUTING
    before = {"status": req.status}
    req.status = SMStatus.COMPUTING.value

    _add_outbox(
        db=db,
        event_type="RUN_SUBMITTED",
        aggregate_type="request",
        aggregate_id=req.id,
        payload={"request_id": str(req.id), "run_ids": run_ids},
    )
    _add_audit(
        db=db,
        user_id=user.id,
        institution_id=user.institution_id,
        action="EXECUTE_REQUEST",
        entity_type="request",
        entity_id=req.id,
        before_state=before,
        after_state={
            "status": req.status,
            "run_ids": run_ids,
            "technique_run_ids": technique_run_ids,
        },
        ip=_client_ip(http_request),
    )
    await _notify_request_owner(
        db,
        req,
        event_type="REQUEST_COMPUTING",
        title="기법 분석 시작",
        body=f"{len(req.cases)}건의 케이스에 대해 {len(techniques)}개 기법 컨테이너 실행이 시작되었습니다.",
    )
    # Commit BEFORE dispatching Celery tasks — the worker uses a separate
    # sync DB session, so TechniqueRun records must be visible (committed)
    # before the task is picked up.
    await db.commit()

    # Dispatch technique execution tasks via Celery
    from app.worker.celery_app import celery_app

    dispatched_task_ids = []
    for tr_id in technique_run_ids:
        task_result = celery_app.send_task(
            "neurohub.tasks.execute_technique_run",
            args=[tr_id],
            queue="compute",
        )
        dispatched_task_ids.append(task_result.id)

    return {
        "request_id": str(req.id),
        "status": req.status,
        "run_ids": run_ids,
        "technique_run_ids": technique_run_ids,
        "technique_count": len(techniques),
        "case_count": len(req.cases),
        "task_ids": dispatched_task_ids,
    }


# ---------------------------------------------------------------------------
# Process endpoint — triggers automatic pipeline for uploaded zip files
# ---------------------------------------------------------------------------


@router.post("/requests/{request_id}/process")
async def process_request(
    request_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
    http_request: FastAPIRequest,
):
    """Trigger automatic processing pipeline for all cases in a request.

    This endpoint:
    1. Finds all uploaded zip files for each case
    2. Transitions the request through STAGING → READY_TO_COMPUTE → COMPUTING
    3. Dispatches a Celery task per case for the full pipeline:
       zip extract → DICOM find → BIDS → Pre-QC → technique exec → fusion

    Roles: PHYSICIAN, TECHNICIAN, SYSTEM_ADMIN
    """
    from app.models.request import CaseFile
    from app.worker.celery_app import celery_app

    req = await _load_request_or_404(db, request_id, user.institution_id, for_update=True)

    # Allow processing from CREATED, RECEIVING, STAGING, or READY_TO_COMPUTE
    allowed_from = {
        SMStatus.CREATED.value,
        SMStatus.RECEIVING.value,
        SMStatus.STAGING.value,
        SMStatus.READY_TO_COMPUTE.value,
    }
    if req.status not in allowed_from:
        raise HTTPException(
            status_code=409,
            detail=f"Request is in {req.status} — cannot process. "
                   f"Allowed: {', '.join(sorted(allowed_from))}",
        )

    # Check that we have uploaded files
    if not req.cases:
        raise HTTPException(status_code=409, detail="No cases found for this request")

    case_tasks = []
    for case in req.cases:
        # Find uploaded zip files for this case
        file_result = await db.execute(
            select(CaseFile).where(
                CaseFile.case_id == case.id,
                CaseFile.upload_status == "COMPLETED",
            )
        )
        case_files = file_result.scalars().all()

        if not case_files:
            raise HTTPException(
                status_code=409,
                detail=f"Case {case.patient_ref} has no uploaded files",
            )

        # Find the zip file (or the first file if no zip)
        zip_file = None
        for cf in case_files:
            if cf.file_name and cf.file_name.lower().endswith(".zip"):
                zip_file = cf
                break
        if not zip_file:
            zip_file = case_files[0]  # Use the first uploaded file

        case_tasks.append({
            "case_id": str(case.id),
            "patient_ref": case.patient_ref,
            "storage_path": zip_file.storage_path,
        })

        # Mark case as READY
        case.status = "READY"

    # Advance request to COMPUTING
    before = {"status": req.status}
    req.status = SMStatus.COMPUTING.value

    _add_audit(
        db=db,
        user_id=user.id,
        institution_id=user.institution_id,
        action="PROCESS_REQUEST",
        entity_type="request",
        entity_id=req.id,
        before_state=before,
        after_state={"status": req.status, "case_count": len(case_tasks)},
        ip=_client_ip(http_request),
    )
    await _notify_request_owner(
        db,
        req,
        event_type="REQUEST_PROCESSING",
        title="자동 분석 시작",
        body=f"{len(case_tasks)}건의 케이스에 대해 자동 분석 파이프라인이 시작되었습니다.",
    )

    # Dispatch outbox event
    _add_outbox(
        db=db,
        event_type="PIPELINE_PROCESS",
        aggregate_type="request",
        aggregate_id=req.id,
        payload={
            "request_id": str(req.id),
            "case_tasks": case_tasks,
        },
    )

    await db.flush()

    # Dispatch Celery tasks directly (also via outbox for reliability)
    task_ids = []
    for ct in case_tasks:
        task_result = celery_app.send_task(
            "neurohub.tasks.process_case_upload",
            args=[str(request_id), ct["case_id"], ct["storage_path"]],
            queue="compute",
        )
        task_ids.append(task_result.id)

    return {
        "request_id": str(req.id),
        "status": req.status,
        "cases_processing": len(case_tasks),
        "task_ids": task_ids,
    }


# ---------------------------------------------------------------------------
# Pipeline status & technique runs (simplified query endpoints)
# ---------------------------------------------------------------------------


@router.get("/requests/{request_id}/pipeline-status")
async def get_pipeline_status(
    request_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Get pipeline processing status for a request.

    Returns current run status, technique run statuses, and stage progress.
    """
    req = await _load_request_or_404(db, request_id, user.institution_id)

    # Get runs for this request
    runs_result = await db.execute(
        select(Run).where(Run.request_id == request_id).order_by(Run.created_at.desc())
    )
    runs = runs_result.scalars().all()

    if not runs:
        return {
            "request_id": str(request_id),
            "request_status": req.status,
            "runs": [],
            "technique_summary": {"total": 0, "pending": 0, "running": 0, "completed": 0, "failed": 0},
        }

    from app.models.technique import TechniqueRun

    run_data = []
    total_stats = {"total": 0, "pending": 0, "running": 0, "completed": 0, "failed": 0}

    for run in runs:
        tr_result = await db.execute(
            select(TechniqueRun).where(TechniqueRun.run_id == run.id).order_by(TechniqueRun.created_at)
        )
        technique_runs = tr_result.scalars().all()

        tr_list = []
        for tr in technique_runs:
            total_stats["total"] += 1
            status_key = tr.status.lower()
            if status_key in total_stats:
                total_stats[status_key] += 1
            elif status_key in ("queued", "pending"):
                total_stats["pending"] += 1

            tr_list.append({
                "id": str(tr.id),
                "technique_key": tr.technique_key,
                "status": tr.status,
                "qc_score": tr.qc_score,
                "started_at": tr.started_at.isoformat() if tr.started_at else None,
                "completed_at": tr.completed_at.isoformat() if tr.completed_at else None,
                "error_detail": tr.error_detail,
            })

        run_data.append({
            "id": str(run.id),
            "case_id": str(run.case_id) if run.case_id else None,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "technique_runs": tr_list,
            "output_data": run.output_data,
        })

    return {
        "request_id": str(request_id),
        "request_status": req.status,
        "runs": run_data,
        "technique_summary": total_stats,
    }


@router.get("/requests/{request_id}/technique-runs")
async def list_request_technique_runs(
    request_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    """List all technique runs for a request (across all runs).

    Simplified endpoint that doesn't require knowing the run_id.
    """
    await _load_request_or_404(db, request_id, user.institution_id)

    from app.models.technique import TechniqueRun

    result = await db.execute(
        select(TechniqueRun, Run.case_id)
        .join(Run, TechniqueRun.run_id == Run.id)
        .where(Run.request_id == request_id)
        .order_by(TechniqueRun.created_at)
    )
    rows = result.all()

    items = []
    for tr, case_id in rows:
        items.append({
            "id": str(tr.id),
            "run_id": str(tr.run_id),
            "case_id": str(case_id) if case_id else None,
            "technique_key": tr.technique_key,
            "status": tr.status,
            "qc_score": tr.qc_score,
            "output_data": tr.output_data,
            "started_at": tr.started_at.isoformat() if tr.started_at else None,
            "completed_at": tr.completed_at.isoformat() if tr.completed_at else None,
            "error_detail": tr.error_detail,
        })

    return {"items": items, "total": len(items)}


# ---------------------------------------------------------------------------
# Download endpoints (PDF report + watermarked file)
# ---------------------------------------------------------------------------


@router.get("/requests/{request_id}/report/download")
async def download_report(
    request_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Return presigned download URL for PDF report."""
    import httpx

    from app.config import settings
    from app.models.report import Report

    await _load_request_or_404(db, request_id, user.institution_id)

    report_result = await db.execute(
        select(Report)
        .where(Report.request_id == request_id)
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    report = report_result.scalar_one_or_none()
    if not report or not report.pdf_storage_path:
        raise HTTPException(status_code=404, detail="PDF report not available")

    bucket = settings.storage_bucket_reports
    from app.services.storage import create_presigned_download as _presign_dl

    signed_url = await _presign_dl(bucket, report.pdf_storage_path, expires_in=900)

    return {
        "download_url": signed_url,
        "filename": f"report-{str(request_id)[:8]}.pdf",
    }


@router.get("/requests/{request_id}/watermarked/download")
async def download_watermarked(
    request_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Return presigned download URL for watermarked file."""
    import httpx

    from app.config import settings
    from app.models.report import Report

    await _load_request_or_404(db, request_id, user.institution_id)

    report_result = await db.execute(
        select(Report)
        .where(Report.request_id == request_id)
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    report = report_result.scalar_one_or_none()
    if not report or not report.watermarked_storage_path:
        raise HTTPException(status_code=404, detail="Watermarked file not available")

    bucket = settings.storage_bucket_outputs
    from app.services.storage import create_presigned_download as _presign_dl

    signed_url = await _presign_dl(bucket, report.watermarked_storage_path, expires_in=900)

    return {
        "download_url": signed_url,
        "filename": f"watermarked-{str(request_id)[:8]}.jpg",
    }
