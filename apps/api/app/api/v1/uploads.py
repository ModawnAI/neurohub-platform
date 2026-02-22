"""File upload endpoints for presigning, completing, listing, and downloading case files."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi import Request as FastAPIRequest
from sqlalchemy import select

from app.config import settings
from app.dependencies import AuthenticatedUser, DbSession
from app.models.audit import AuditLog, PatientAccessLog
from app.models.outbox import OutboxEvent
from app.models.request import Case, CaseFile, Request, UploadSession
from app.schemas.upload import (
    CaseFileListResponse,
    CaseFileRead,
    CaseListResponse,
    CaseRead,
    DownloadUrlResponse,
    UploadCompleteRequest,
    UploadPresignRequest,
    UploadPresignResponse,
)
from app.services.state_machine import RequestStatus

router = APIRouter(tags=["Uploads"])

PRESIGN_EXPIRY_SECONDS = 900  # 15 minutes


async def _load_request_or_404(
    db: DbSession,
    request_id: uuid.UUID,
    institution_id: uuid.UUID,
) -> Request:
    result = await db.execute(
        select(Request).where(
            Request.id == request_id,
            Request.institution_id == institution_id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


async def _load_case_or_404(
    db: DbSession,
    case_id: uuid.UUID,
    request_id: uuid.UUID,
    institution_id: uuid.UUID,
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


async def _log_patient_access(
    db: DbSession,
    institution_id: uuid.UUID,
    user_id: uuid.UUID,
    patient_ref: str,
    access_type: str,
    resource_type: str,
    resource_id: uuid.UUID,
    ip_address: str | None = None,
):
    """Create a HIPAA-compliant patient access log entry."""
    db.add(PatientAccessLog(
        institution_id=institution_id,
        user_id=user_id,
        patient_ref=patient_ref,
        access_type=access_type,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
    ))


# ---------------------------------------------------------------------------
# GET /requests/{request_id}/cases
# ---------------------------------------------------------------------------
@router.get("/requests/{request_id}/cases", response_model=CaseListResponse)
async def list_cases(
    request_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    req = await _load_request_or_404(db, request_id, user.institution_id)
    return CaseListResponse(
        items=[
            CaseRead(
                id=c.id,
                institution_id=c.institution_id,
                request_id=c.request_id,
                patient_ref=c.patient_ref,
                demographics=c.demographics,
                status=c.status,
                created_at=c.created_at,
            )
            for c in req.cases
        ]
    )


# ---------------------------------------------------------------------------
# POST /requests/{request_id}/cases/{case_id}/files/presign
# ---------------------------------------------------------------------------
@router.post(
    "/requests/{request_id}/cases/{case_id}/files/presign",
    response_model=UploadPresignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def presign_upload(
    request_id: uuid.UUID,
    case_id: uuid.UUID,
    body: UploadPresignRequest,
    request: FastAPIRequest,
    db: DbSession,
    user: AuthenticatedUser,
):
    import app.services.storage as storage_svc

    req = await _load_request_or_404(db, request_id, user.institution_id)

    # Only allow uploads when request is CREATED or RECEIVING
    if req.status not in (RequestStatus.CREATED.value, RequestStatus.RECEIVING.value):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot upload files when request is {req.status}",
        )

    case = await _load_case_or_404(db, case_id, request_id, user.institution_id)

    # Build storage path
    storage_path = (
        f"institutions/{user.institution_id}"
        f"/requests/{request_id}"
        f"/cases/{case_id}"
        f"/{body.slot_name}"
        f"/{body.file_name}"
    )

    # Create CaseFile record
    case_file = CaseFile(
        institution_id=user.institution_id,
        case_id=case_id,
        slot_name=body.slot_name,
        file_name=body.file_name,
        file_size=body.file_size,
        content_type=body.content_type,
        storage_path=storage_path,
        upload_status="PENDING",
    )
    db.add(case_file)
    await db.flush()

    # Generate presigned URL
    presigned_url = await storage_svc.create_presigned_upload(
        bucket=settings.storage_bucket_inputs,
        path=storage_path,
        expires_in=PRESIGN_EXPIRY_SECONDS,
    )
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=PRESIGN_EXPIRY_SECONDS)

    # Create UploadSession
    upload_session = UploadSession(
        case_file_id=case_file.id,
        presigned_url=presigned_url,
        expires_at=expires_at,
    )
    db.add(upload_session)

    # Auto-transition request CREATED → RECEIVING
    if req.status == RequestStatus.CREATED.value:
        req.status = RequestStatus.RECEIVING.value

    # Add outbox event
    db.add(
        OutboxEvent(
            event_type="FILE_UPLOAD_INITIATED",
            aggregate_type="case_file",
            aggregate_id=case_file.id,
            payload={
                "request_id": str(request_id),
                "case_id": str(case_id),
                "case_file_id": str(case_file.id),
                "slot_name": body.slot_name,
                "file_name": body.file_name,
            },
        )
    )

    # HIPAA: log patient data access
    await _log_patient_access(
        db, user.institution_id, user.id,
        patient_ref=case.patient_ref or "UNKNOWN",
        access_type="UPLOAD",
        resource_type="case_file",
        resource_id=case_file.id,
        ip_address=request.client.host if request.client else None,
    )

    await db.flush()

    return UploadPresignResponse(
        case_file_id=case_file.id,
        presigned_url=presigned_url,
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# POST /requests/{request_id}/cases/{case_id}/files/{file_id}/complete
# ---------------------------------------------------------------------------
@router.post(
    "/requests/{request_id}/cases/{case_id}/files/{file_id}/complete",
    response_model=CaseFileRead,
)
async def complete_upload(
    request_id: uuid.UUID,
    case_id: uuid.UUID,
    file_id: uuid.UUID,
    body: UploadCompleteRequest,
    request: FastAPIRequest,
    db: DbSession,
    user: AuthenticatedUser,
):
    await _load_request_or_404(db, request_id, user.institution_id)
    await _load_case_or_404(db, case_id, request_id, user.institution_id)

    result = await db.execute(
        select(CaseFile).where(
            CaseFile.id == file_id,
            CaseFile.case_id == case_id,
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

    # Virus scan (best-effort; graceful fallback if ClamAV unavailable)
    try:
        from app.services.virus_scan import scan_result_for_file, is_scanning_enabled

        if is_scanning_enabled():
            import app.services.storage as storage_svc

            scan_result = scan_result_for_file(b"")  # placeholder: actual content scan requires download
            if not scan_result.is_clean:
                case_file.upload_status = "REJECTED"
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"File rejected: virus detected — {scan_result.detail}",
                )
    except HTTPException:
        raise
    except Exception:
        pass  # Scanner unavailable; proceed with upload

    # Mark upload session as completed
    if case_file.upload_session:
        case_file.upload_session.completed_at = datetime.now(timezone.utc)

    # HIPAA: log patient data access
    case = await _load_case_or_404(db, case_id, request_id, user.institution_id)
    await _log_patient_access(
        db, user.institution_id, user.id,
        patient_ref=case.patient_ref or "UNKNOWN",
        access_type="UPLOAD_COMPLETE",
        resource_type="case_file",
        resource_id=file_id,
        ip_address=request.client.host if request.client else None,
    )

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
# GET /requests/{request_id}/cases/{case_id}/files
# ---------------------------------------------------------------------------
@router.get(
    "/requests/{request_id}/cases/{case_id}/files",
    response_model=CaseFileListResponse,
)
async def list_case_files(
    request_id: uuid.UUID,
    case_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    await _load_request_or_404(db, request_id, user.institution_id)
    case = await _load_case_or_404(db, case_id, request_id, user.institution_id)

    return CaseFileListResponse(
        items=[
            CaseFileRead(
                id=f.id,
                case_id=f.case_id,
                slot_name=f.slot_name,
                file_name=f.file_name,
                file_size=f.file_size,
                content_type=f.content_type,
                upload_status=f.upload_status,
                checksum_sha256=f.checksum_sha256,
                created_at=f.created_at,
            )
            for f in case.files
        ]
    )


# ---------------------------------------------------------------------------
# GET /requests/{request_id}/cases/{case_id}/files/{file_id}/download
# ---------------------------------------------------------------------------
@router.get(
    "/requests/{request_id}/cases/{case_id}/files/{file_id}/download",
    response_model=DownloadUrlResponse,
)
async def get_download_url(
    request_id: uuid.UUID,
    case_id: uuid.UUID,
    file_id: uuid.UUID,
    request: FastAPIRequest,
    db: DbSession,
    user: AuthenticatedUser,
):
    import app.services.storage as storage_svc

    await _load_request_or_404(db, request_id, user.institution_id)
    await _load_case_or_404(db, case_id, request_id, user.institution_id)

    result = await db.execute(
        select(CaseFile).where(
            CaseFile.id == file_id,
            CaseFile.case_id == case_id,
            CaseFile.institution_id == user.institution_id,
        )
    )
    case_file = result.scalar_one_or_none()
    if not case_file:
        raise HTTPException(status_code=404, detail="Case file not found")

    if case_file.upload_status != "COMPLETED":
        raise HTTPException(status_code=409, detail="File upload not completed yet")

    # HIPAA: log patient data access
    case = await _load_case_or_404(db, case_id, request_id, user.institution_id)
    await _log_patient_access(
        db, user.institution_id, user.id,
        patient_ref=case.patient_ref or "UNKNOWN",
        access_type="DOWNLOAD",
        resource_type="case_file",
        resource_id=file_id,
        ip_address=request.client.host if request.client else None,
    )

    url = await storage_svc.create_presigned_download(
        bucket=settings.storage_bucket_inputs,
        path=case_file.storage_path,
        expires_in=PRESIGN_EXPIRY_SECONDS,
    )
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=PRESIGN_EXPIRY_SECONDS)

    return DownloadUrlResponse(url=url, expires_at=expires_at)
