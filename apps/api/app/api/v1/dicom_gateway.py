"""DICOM Gateway API — STOW-RS ingestion, study management, DICOM SCP."""

import uuid
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, func

from app.config import settings
from app.dependencies import AuthenticatedUser, CurrentUser, DbSession, get_current_user
from app.models.dicom_study import DicomStudy
from app.schemas.dicom_gateway import (
    CreateRequestFromStudyRequest,
    DicomStudyList,
    DicomStudyRead,
    LinkStudyRequest,
)

logger = logging.getLogger("neurohub.dicom_gateway")

router = APIRouter(prefix="/dicom", tags=["dicom"])


# ---------------------------------------------------------------------------
# Dependency: require admin scope
# ---------------------------------------------------------------------------

async def require_admin(user: CurrentUser = Depends(get_current_user)):
    """Ensure the authenticated user has admin privileges."""
    is_admin_role = user.has_any_role("SYSTEM_ADMIN", "ADMIN")
    is_admin_type = user.user_type == "ADMIN"
    if not (is_admin_role or is_admin_type):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


# ---------------------------------------------------------------------------
# Study listing & detail
# ---------------------------------------------------------------------------

@router.get("/studies", response_model=DicomStudyList)
async def list_studies(
    db: DbSession,
    user: AuthenticatedUser,
    status_filter: str | None = Query(None, alias="status"),
    modality: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List DICOM studies for the user's institution."""
    q = select(DicomStudy).where(DicomStudy.institution_id == user.institution_id)
    count_q = select(func.count()).select_from(DicomStudy).where(
        DicomStudy.institution_id == user.institution_id
    )

    if status_filter:
        q = q.where(DicomStudy.status == status_filter)
        count_q = count_q.where(DicomStudy.status == status_filter)
    if modality:
        q = q.where(DicomStudy.modality == modality)
        count_q = count_q.where(DicomStudy.modality == modality)
    if date_from:
        q = q.where(DicomStudy.study_date >= date_from)
        count_q = count_q.where(DicomStudy.study_date >= date_from)
    if date_to:
        q = q.where(DicomStudy.study_date <= date_to)
        count_q = count_q.where(DicomStudy.study_date <= date_to)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(DicomStudy.created_at.desc()).offset(offset).limit(limit)
    )
    items = result.scalars().all()
    return DicomStudyList(
        items=[DicomStudyRead.model_validate(s) for s in items],
        total=total,
    )


@router.get("/studies/{study_uid}", response_model=DicomStudyRead)
async def get_study(study_uid: str, db: DbSession, user: AuthenticatedUser):
    """Get a single DICOM study by study_instance_uid."""
    result = await db.execute(
        select(DicomStudy).where(
            DicomStudy.study_instance_uid == study_uid,
            DicomStudy.institution_id == user.institution_id,
        )
    )
    study = result.scalars().first()
    if not study:
        raise HTTPException(404, "Study not found")
    return DicomStudyRead.model_validate(study)


@router.get("/worklist", response_model=DicomStudyList)
async def get_worklist(db: DbSession, user: AuthenticatedUser):
    """Get RECEIVED (unlinked) studies as a worklist."""
    q = (
        select(DicomStudy)
        .where(
            DicomStudy.institution_id == user.institution_id,
            DicomStudy.status == "RECEIVED",
            DicomStudy.request_id.is_(None),
        )
        .order_by(DicomStudy.created_at.desc())
        .limit(100)
    )
    result = await db.execute(q)
    items = result.scalars().all()
    return DicomStudyList(
        items=[DicomStudyRead.model_validate(s) for s in items],
        total=len(items),
    )


# ---------------------------------------------------------------------------
# Link study to existing request
# ---------------------------------------------------------------------------

@router.post("/studies/{study_uid}/link", response_model=DicomStudyRead)
async def link_study_to_request(
    study_uid: str,
    body: LinkStudyRequest,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Link a DICOM study to an existing analysis request."""
    result = await db.execute(
        select(DicomStudy).where(
            DicomStudy.study_instance_uid == study_uid,
            DicomStudy.institution_id == user.institution_id,
        )
    )
    study = result.scalars().first()
    if not study:
        raise HTTPException(404, "Study not found")

    from app.models.request import Request as AnalysisRequest

    req = await db.get(AnalysisRequest, body.request_id)
    if not req or req.institution_id != user.institution_id:
        raise HTTPException(404, "Request not found")

    study.request_id = body.request_id
    study.status = "LINKED"
    await db.commit()
    await db.refresh(study)
    return DicomStudyRead.model_validate(study)


# ---------------------------------------------------------------------------
# Create new request from DICOM study
# ---------------------------------------------------------------------------

@router.post("/studies/{study_uid}/create-request", response_model=DicomStudyRead)
async def create_request_from_study(
    study_uid: str,
    body: CreateRequestFromStudyRequest,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Create a new analysis request from a DICOM study."""
    result = await db.execute(
        select(DicomStudy).where(
            DicomStudy.study_instance_uid == study_uid,
            DicomStudy.institution_id == user.institution_id,
        )
    )
    study = result.scalars().first()
    if not study:
        raise HTTPException(404, "Study not found")

    from app.models.request import Case, Request as AnalysisRequest
    from app.models.service import PipelineDefinition, ServiceDefinition

    svc = await db.get(ServiceDefinition, body.service_id)
    if not svc:
        raise HTTPException(404, "Service not found")

    # Find default pipeline for the service
    pipe_result = await db.execute(
        select(PipelineDefinition)
        .where(PipelineDefinition.service_id == body.service_id)
        .order_by(PipelineDefinition.created_at.asc())
        .limit(1)
    )
    pipeline = pipe_result.scalars().first()
    if not pipeline:
        raise HTTPException(400, "Service has no pipeline configured")

    new_request = AnalysisRequest(
        institution_id=user.institution_id,
        service_id=body.service_id,
        pipeline_id=pipeline.id,
        requested_by=user.id,
        status="CREATED",
        priority=5,
        service_snapshot={
            "name": svc.name,
            "display_name": svc.display_name,
            "version": svc.version,
        },
        pipeline_snapshot={
            "name": pipeline.name,
            "version": pipeline.version,
            "steps": pipeline.steps or [],
            "qc_rules": pipeline.qc_rules or {},
        },
    )
    db.add(new_request)
    await db.flush()

    # Create a case from the DICOM patient info
    db.add(Case(
        institution_id=user.institution_id,
        request_id=new_request.id,
        patient_ref=study.patient_id or "UNKNOWN",
        demographics={
            "patient_name": study.patient_name,
            "modality": study.modality,
            "study_date": str(study.study_date) if study.study_date else None,
        },
        status="CREATED",
    ))

    study.request_id = new_request.id
    study.status = "LINKED"
    await db.commit()
    await db.refresh(study)
    return DicomStudyRead.model_validate(study)


# ---------------------------------------------------------------------------
# STOW-RS: POST /dicom/studies  (must be AFTER GET /dicom/studies)
# ---------------------------------------------------------------------------

@router.post("/stow-rs", status_code=status.HTTP_200_OK)
async def stow_rs_store(request: Request, user: CurrentUser = Depends(get_current_user)):
    """Accept DICOM instances via STOW-RS (multipart/related)."""
    from app.services.dicom_service import parse_dicom_multipart, store_dicom_instance

    content_type = request.headers.get("content-type", "")
    if "multipart/related" not in content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Expected multipart/related content-type",
        )

    body = await request.body()
    try:
        instances = parse_dicom_multipart(body, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    institution_id = uuid.UUID(settings.default_institution_id)
    results = []
    for dicom_bytes in instances:
        try:
            result = await store_dicom_instance(dicom_bytes, institution_id, received_via="STOW_RS")
            results.append({"status": "stored", "storage_path": result["storage_path"]})
        except Exception as exc:
            logger.exception("Failed to store DICOM instance")
            results.append({"status": "error", "detail": str(exc)})

    return JSONResponse(content={"instances": results})


# ---------------------------------------------------------------------------
# SCP Management endpoints (admin only)
# ---------------------------------------------------------------------------

@router.post("/scp/start", status_code=status.HTTP_200_OK)
async def start_scp_endpoint(
    institution_id: uuid.UUID | None = None,
    admin=Depends(require_admin),
):
    """Start the DICOM C-STORE SCP listener (admin only)."""
    from app.services import pacs_service

    if pacs_service._scp_running:
        return {"status": "already_running", **pacs_service.get_scp_status()}

    iid = institution_id or uuid.UUID(settings.default_institution_id)
    await pacs_service.start_scp(iid)
    return {"status": "started", **pacs_service.get_scp_status()}


@router.post("/scp/stop", status_code=status.HTTP_200_OK)
async def stop_scp_endpoint(admin=Depends(require_admin)):
    """Stop the DICOM C-STORE SCP listener (admin only)."""
    from app.services import pacs_service

    await pacs_service.stop_scp()
    return {"status": "stopped", **pacs_service.get_scp_status()}


@router.get("/scp/status", status_code=status.HTTP_200_OK)
async def scp_status_endpoint(user: CurrentUser = Depends(get_current_user)):
    """Get current DICOM SCP status (running/stopped, port, AE title)."""
    from app.services import pacs_service

    return pacs_service.get_scp_status()
