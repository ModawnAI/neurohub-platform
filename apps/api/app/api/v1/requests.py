import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from fastapi import Request as FastAPIRequest
from sqlalchemy import func, select

from app.dependencies import AuthenticatedUser, DbSession
from app.models.audit import AuditLog
from app.models.idempotency import IdempotencyKey
from app.models.outbox import OutboxEvent
from app.models.request import Case, Request
from app.models.run import Run, RunStep
from app.models.service import PipelineDefinition, ServiceDefinition
from app.schemas.pagination import PaginatedResponse
from app.schemas.request import (
    CancelRequest,
    ConfirmRequest,
    RequestCreate,
    RequestRead,
    RequestStatus,
    TransitionRequest,
)
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


def _to_read(req: Request) -> RequestRead:
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
        raise HTTPException(status_code=409, detail="Invalid idempotency resource reference") from exc

    return await _load_request_or_404(db, request_id, institution_id)


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
            return _to_read(existing)

        idempotency_record = IdempotencyKey(
            scope=IDEMPOTENCY_SCOPE_UI_REQUEST,
            idempotency_key=body.idempotency_key,
            request_hash=payload_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=IDEMPOTENCY_TTL_HOURS),
        )
        db.add(idempotency_record)

    svc_result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == body.service_id,
            ServiceDefinition.institution_id == user.institution_id,
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
    count_query = select(func.count(Request.id)).where(Request.institution_id == user.institution_id)

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
):
    req = await _load_request_or_404(db, request_id, user.institution_id)
    return _to_read(req)


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
    await db.flush()
    return {"request_id": str(req.id), "status": req.status, "run_ids": run_ids}
