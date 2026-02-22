"""B2B API endpoints — dedicated routes for API key–authenticated integrations."""

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi import Request as FastAPIRequest
from sqlalchemy import select

from app.dependencies import AuthenticatedUser, DbSession
from app.models.audit import AuditLog
from app.models.idempotency import IdempotencyKey
from app.models.outbox import OutboxEvent
from app.models.request import Case, CaseFile, Request, UploadSession
from app.models.service import PipelineDefinition, ServiceDefinition
from pydantic import BaseModel, Field

from app.schemas.request import RequestCreate, RequestRead, RequestStatus
from app.schemas.upload import (
    CaseFileRead,
    DownloadUrlResponse,
    UploadCompleteRequest,
    UploadPresignRequest,
    UploadPresignResponse,
)
from app.services.state_machine import RequestStatus as SMStatus

router = APIRouter(prefix="/b2b", tags=["B2B"])

IDEMPOTENCY_SCOPE_B2B = "B2B_REQUEST"
IDEMPOTENCY_TTL_HOURS = 24
PRESIGN_EXPIRY_SECONDS = 900


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


async def _load_request_or_404(
    db: DbSession, request_id: uuid.UUID, institution_id: uuid.UUID
) -> Request:
    result = await db.execute(
        select(Request).where(
            Request.id == request_id, Request.institution_id == institution_id
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


async def _load_case_or_404(
    db: DbSession, case_id: uuid.UUID, request_id: uuid.UUID, institution_id: uuid.UUID
) -> Case:
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.request_id == request_id,
            Case.institution_id == institution_id,
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


# ---------------------------------------------------------------------------
# POST /b2b/requests — Create request via API key
# ---------------------------------------------------------------------------
@router.post("/requests", response_model=RequestRead, status_code=status.HTTP_201_CREATED)
async def b2b_create_request(
    body: RequestCreate,
    db: DbSession,
    user: AuthenticatedUser,
    http_request: FastAPIRequest,
):
    payload_hash: str | None = None
    idempotency_record: IdempotencyKey | None = None

    if body.idempotency_key:
        payload_hash = _canonical_payload_hash(body)
        idem_result = await db.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.scope == IDEMPOTENCY_SCOPE_B2B,
                IdempotencyKey.idempotency_key == body.idempotency_key,
            )
        )
        idem = idem_result.scalar_one_or_none()
        if idem:
            if idem.request_hash != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "IDEMPOTENCY_CONFLICT",
                        "message": "Same idempotency key was used with different payload.",
                        "idempotency_key": body.idempotency_key,
                    },
                )
            if idem.resource_type == "request" and idem.resource_id:
                existing = await _load_request_or_404(
                    db, uuid.UUID(idem.resource_id), user.institution_id
                )
                return _to_read(existing)

        idempotency_record = IdempotencyKey(
            scope=IDEMPOTENCY_SCOPE_B2B,
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

    db.add(
        AuditLog(
            user_id=user.id,
            institution_id=user.institution_id,
            action="B2B_CREATE_REQUEST",
            entity_type="request",
            entity_id=req.id,
            before_state=None,
            after_state={"status": req.status},
            ip_address=_client_ip(http_request),
        )
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


# ---------------------------------------------------------------------------
# GET /b2b/requests/{request_id} — Get request via API key
# ---------------------------------------------------------------------------
@router.get("/requests/{request_id}", response_model=RequestRead)
async def b2b_get_request(
    request_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    req = await _load_request_or_404(db, request_id, user.institution_id)
    return _to_read(req)


# ---------------------------------------------------------------------------
# POST /b2b/requests/{request_id}/files/presign
# ---------------------------------------------------------------------------
@router.post(
    "/requests/{request_id}/files/presign",
    response_model=UploadPresignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def b2b_presign_upload(
    request_id: uuid.UUID,
    body: UploadPresignRequest,
    db: DbSession,
    user: AuthenticatedUser,
):
    import app.services.storage as storage_svc
    from app.config import settings

    req = await _load_request_or_404(db, request_id, user.institution_id)

    if req.status not in (SMStatus.CREATED.value, SMStatus.RECEIVING.value):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot upload files when request is {req.status}",
        )

    # B2B presign requires case_id in body
    if not body.case_id:
        raise HTTPException(status_code=422, detail="case_id is required for B2B uploads")

    case = await _load_case_or_404(db, body.case_id, request_id, user.institution_id)

    storage_path = (
        f"institutions/{user.institution_id}"
        f"/requests/{request_id}"
        f"/cases/{case.id}"
        f"/{body.slot_name}"
        f"/{body.file_name}"
    )

    case_file = CaseFile(
        institution_id=user.institution_id,
        case_id=case.id,
        slot_name=body.slot_name,
        file_name=body.file_name,
        file_size=body.file_size,
        content_type=body.content_type,
        storage_path=storage_path,
        upload_status="PENDING",
    )
    db.add(case_file)
    await db.flush()

    presigned_url = await storage_svc.create_presigned_upload(
        bucket=settings.storage_bucket_inputs,
        path=storage_path,
        expires_in=PRESIGN_EXPIRY_SECONDS,
    )
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=PRESIGN_EXPIRY_SECONDS)

    upload_session = UploadSession(
        case_file_id=case_file.id,
        presigned_url=presigned_url,
        expires_at=expires_at,
    )
    db.add(upload_session)

    if req.status == SMStatus.CREATED.value:
        req.status = SMStatus.RECEIVING.value

    db.add(
        OutboxEvent(
            event_type="FILE_UPLOAD_INITIATED",
            aggregate_type="case_file",
            aggregate_id=case_file.id,
            payload={
                "request_id": str(request_id),
                "case_id": str(case.id),
                "case_file_id": str(case_file.id),
                "slot_name": body.slot_name,
                "file_name": body.file_name,
                "source": "b2b",
            },
        )
    )
    await db.flush()

    return UploadPresignResponse(
        case_file_id=case_file.id,
        presigned_url=presigned_url,
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# POST /b2b/requests/{request_id}/files/complete
# ---------------------------------------------------------------------------
@router.post("/requests/{request_id}/files/complete", response_model=CaseFileRead)
async def b2b_complete_upload(
    request_id: uuid.UUID,
    body: UploadCompleteRequest,
    db: DbSession,
    user: AuthenticatedUser,
):
    await _load_request_or_404(db, request_id, user.institution_id)

    if not body.case_file_id:
        raise HTTPException(status_code=422, detail="case_file_id is required for B2B uploads")

    result = await db.execute(
        select(CaseFile).where(
            CaseFile.id == body.case_file_id,
            CaseFile.institution_id == user.institution_id,
        )
    )
    case_file = result.scalar_one_or_none()
    if not case_file:
        raise HTTPException(status_code=404, detail="Case file not found")

    if case_file.upload_status == "COMPLETED":
        raise HTTPException(status_code=409, detail="Upload already completed")

    case_file.upload_status = "COMPLETED"
    case_file.checksum_sha256 = body.checksum_sha256

    if case_file.upload_session:
        case_file.upload_session.completed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(case_file)

    return CaseFileRead(
        id=case_file.id,
        case_id=case_file.case_id,
        slot_name=case_file.slot_name,
        file_name=case_file.file_name,
        file_size=case_file.file_size,
        content_type=case_file.content_type,
        upload_status=case_file.upload_status,
        checksum_sha256=case_file.checksum_sha256,
        created_at=case_file.created_at,
    )


# ---------------------------------------------------------------------------
# POST /b2b/requests/batch — Batch create requests
# ---------------------------------------------------------------------------
class BatchRequestCreate(BaseModel):
    requests: list[dict] = Field(..., min_length=1, max_length=50)


@router.post("/requests/batch", status_code=status.HTTP_207_MULTI_STATUS)
async def batch_create_requests(
    body: BatchRequestCreate,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Create multiple requests in a single call. Returns per-request results."""
    results = []
    for i, req_data in enumerate(body.requests):
        try:
            # Create each request individually
            service_id = uuid.UUID(req_data.get("service_id", ""))
            pipeline_id = uuid.UUID(req_data.get("pipeline_id", ""))
            cases_data = req_data.get("cases", [])
            idempotency_key = req_data.get("idempotency_key")
            priority = req_data.get("priority", 5)

            request = Request(
                institution_id=user.institution_id,
                requester_id=user.id,
                service_id=service_id,
                pipeline_id=pipeline_id,
                status="CREATED",
                priority=priority,
            )
            db.add(request)
            await db.flush()

            for case_data in cases_data:
                case = Case(
                    institution_id=user.institution_id,
                    request_id=request.id,
                    patient_ref=case_data.get("patient_ref", ""),
                    demographics=case_data.get("demographics"),
                )
                db.add(case)

            db.add(OutboxEvent(
                event_type="REQUEST_CREATED",
                aggregate_type="request",
                aggregate_id=request.id,
                payload={"request_id": str(request.id), "source": "B2B_BATCH"},
            ))

            await db.flush()
            results.append({"index": i, "status": "success", "id": str(request.id)})
        except Exception as e:
            results.append({"index": i, "status": "error", "error": str(e)})

    return {"results": results, "total": len(results), "succeeded": sum(1 for r in results if r["status"] == "success")}
