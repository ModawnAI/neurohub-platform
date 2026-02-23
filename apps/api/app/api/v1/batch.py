"""Batch request creation API — atomic batch creation with validation."""

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi import Request as FastAPIRequest
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.dependencies import AuthenticatedUser, DbSession
from app.models.audit import AuditLog
from app.models.idempotency import IdempotencyKey
from app.models.outbox import OutboxEvent
from app.models.request import Case, Request
from app.models.service import PipelineDefinition, ServiceDefinition
from app.schemas.request import RequestCreate, RequestRead, RequestStatus
from app.services.state_machine import RequestStatus as SMStatus

router = APIRouter(tags=["Batch"])

IDEMPOTENCY_SCOPE_BATCH = "BATCH_REQUEST"
IDEMPOTENCY_TTL_HOURS = 24
MAX_BATCH_SIZE = 50


class BatchRequestPayload(BaseModel):
    requests: list[RequestCreate] = Field(..., min_length=1, max_length=MAX_BATCH_SIZE)


class BatchResultItem(BaseModel):
    index: int
    id: uuid.UUID


class BatchResponse(BaseModel):
    created: list[BatchResultItem]
    total: int


def _client_ip(req: FastAPIRequest) -> str | None:
    return req.client.host if req.client else None


def _canonical_payload_hash(body: RequestCreate) -> str:
    payload = body.model_dump(mode="json", exclude={"idempotency_key"})
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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


@router.post(
    "/batch/requests",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def batch_create_requests(
    body: BatchRequestPayload,
    db: DbSession,
    user: AuthenticatedUser,
    http_request: FastAPIRequest,
):
    """Create multiple requests atomically.

    All requests are validated before any are created. If any single request
    fails validation, the entire batch is rejected (no partial creates).
    """
    institution_id = user.institution_id

    # ---------- Phase 1: Validate all requests ----------
    # Collect unique service/pipeline IDs to batch-load
    service_ids = {r.service_id for r in body.requests}
    pipeline_ids = {r.pipeline_id for r in body.requests}

    # Load all referenced services
    svc_result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id.in_(service_ids),
            ServiceDefinition.institution_id == institution_id,
        )
    )
    services = {s.id: s for s in svc_result.scalars().all()}

    # Load all referenced pipelines
    pipe_result = await db.execute(
        select(PipelineDefinition).where(
            PipelineDefinition.id.in_(pipeline_ids),
        )
    )
    pipelines = {p.id: p for p in pipe_result.scalars().all()}

    # Check idempotency keys for duplicates within batch
    idem_keys = [r.idempotency_key for r in body.requests if r.idempotency_key]
    if len(idem_keys) != len(set(idem_keys)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Duplicate idempotency keys within batch",
        )

    # Validate each request
    errors: list[dict] = []
    for i, req_body in enumerate(body.requests):
        if req_body.service_id not in services:
            errors.append({"index": i, "detail": f"Service {req_body.service_id} not found"})
            continue
        svc = services[req_body.service_id]
        if req_body.pipeline_id not in pipelines:
            errors.append({"index": i, "detail": f"Pipeline {req_body.pipeline_id} not found"})
            continue
        pipe = pipelines[req_body.pipeline_id]
        if pipe.service_id != svc.id:
            errors.append({
                "index": i,
                "detail": f"Pipeline {req_body.pipeline_id} does not belong to service {svc.id}",
            })

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": errors, "message": "Batch validation failed — no requests created"},
        )

    # ---------- Phase 2: Create all requests ----------
    created_items: list[BatchResultItem] = []

    for i, req_body in enumerate(body.requests):
        svc = services[req_body.service_id]
        pipe = pipelines[req_body.pipeline_id]

        # Idempotency handling
        if req_body.idempotency_key:
            payload_hash = _canonical_payload_hash(req_body)
            idem_result = await db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.scope == IDEMPOTENCY_SCOPE_BATCH,
                    IdempotencyKey.idempotency_key == req_body.idempotency_key,
                )
            )
            existing_idem = idem_result.scalar_one_or_none()
            if existing_idem:
                if existing_idem.request_hash != payload_hash:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "error": "IDEMPOTENCY_CONFLICT",
                            "message": f"Request at index {i}: same idempotency key with different payload",
                            "idempotency_key": req_body.idempotency_key,
                        },
                    )
                if existing_idem.resource_id:
                    created_items.append(
                        BatchResultItem(index=i, id=uuid.UUID(existing_idem.resource_id))
                    )
                    continue

            db.add(IdempotencyKey(
                scope=IDEMPOTENCY_SCOPE_BATCH,
                idempotency_key=req_body.idempotency_key,
                request_hash=payload_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=IDEMPOTENCY_TTL_HOURS),
            ))

        req = Request(
            institution_id=institution_id,
            service_id=svc.id,
            pipeline_id=pipe.id,
            status=SMStatus.CREATED.value,
            priority=req_body.priority,
            inputs=req_body.inputs,
            options=req_body.options,
            requested_by=user.id,
            service_snapshot={
                "name": svc.name,
                "display_name": svc.display_name,
                "version": svc.version,
            },
            pipeline_snapshot={
                "name": pipe.name,
                "version": pipe.version,
                "steps": pipe.steps or [],
                "qc_rules": pipe.qc_rules or {},
            },
            idempotency_key=req_body.idempotency_key,
        )
        db.add(req)
        await db.flush()

        for case_payload in req_body.cases:
            db.add(Case(
                institution_id=institution_id,
                request_id=req.id,
                patient_ref=case_payload.patient_ref,
                demographics=case_payload.demographics,
                status="CREATED",
            ))

        db.add(AuditLog(
            user_id=user.id,
            institution_id=institution_id,
            action="BATCH_CREATE_REQUEST",
            entity_type="request",
            entity_id=req.id,
            before_state=None,
            after_state={"status": req.status, "batch_index": i},
            ip_address=_client_ip(http_request),
        ))

        db.add(OutboxEvent(
            event_type="REQUEST_CREATED",
            aggregate_type="request",
            aggregate_id=req.id,
            payload={"request_id": str(req.id), "source": "BATCH"},
        ))

        # Update idempotency record if present
        if req_body.idempotency_key:
            idem_result2 = await db.execute(
                select(IdempotencyKey).where(
                    IdempotencyKey.scope == IDEMPOTENCY_SCOPE_BATCH,
                    IdempotencyKey.idempotency_key == req_body.idempotency_key,
                )
            )
            idem_record = idem_result2.scalar_one_or_none()
            if idem_record:
                idem_record.resource_type = "request"
                idem_record.resource_id = str(req.id)
                idem_record.response_status = 201

        created_items.append(BatchResultItem(index=i, id=req.id))

    await db.flush()

    return BatchResponse(created=created_items, total=len(created_items))
