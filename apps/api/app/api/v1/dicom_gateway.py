"""DICOMweb Gateway — STOW-RS (store), WADO-RS (retrieve), and study management."""

import logging
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import AuthenticatedUser, DbSession, require_roles
from app.models.dicom_study import DicomSeries, DicomStudy
from app.schemas.dicom_gateway import (
    CreateRequestFromStudyRequest,
    DicomStudyList,
    DicomStudyRead,
    LinkStudyRequest,
    StowRsResponse,
    StowRsResult,
)
from app.services.dicom_service import (
    create_request_from_study,
    get_dicom_metadata,
    parse_dicom_multipart,
    store_dicom_instance,
)

router = APIRouter(prefix="/dicom", tags=["DICOM Gateway"])
logger = logging.getLogger("neurohub.dicom_gateway")


# ─── STOW-RS (Store) ────────────────────────────────────────────────────────

@router.post("/studies", response_model=StowRsResponse)
async def stow_rs_store(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("ADMIN", "SERVICE_USER"))],
    db: DbSession,
):
    """STOW-RS: Receive multipart/related DICOM instances from a PACS system."""
    content_type = request.headers.get("content-type", "")
    if "multipart/related" not in content_type.lower():
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Expected multipart/related content-type",
        )

    body = await request.body()
    try:
        dicom_parts = parse_dicom_multipart(body, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    institution_id = user.institution_id
    results: list[StowRsResult] = []
    study_cache: dict[str, DicomStudy] = {}
    series_cache: dict[str, DicomSeries] = {}

    source_aet = request.headers.get("X-DICOM-AE-Title") or request.headers.get("calling-aet")

    for dicom_bytes in dicom_parts:
        try:
            meta = get_dicom_metadata(dicom_bytes)
        except Exception as exc:
            logger.warning("Failed to parse DICOM instance: %s", exc)
            results.append(StowRsResult(
                study_instance_uid="",
                series_instance_uid="",
                sop_instance_uid="",
                status="failure",
                reason=str(exc),
            ))
            continue

        study_uid = meta["study_instance_uid"]
        series_uid = meta["series_instance_uid"]
        sop_uid = meta["sop_instance_uid"]

        if not study_uid or not series_uid or not sop_uid:
            results.append(StowRsResult(
                study_instance_uid=study_uid,
                series_instance_uid=series_uid,
                sop_instance_uid=sop_uid,
                status="failure",
                reason="Missing required DICOM UIDs",
            ))
            continue

        # Get or create DicomStudy
        if study_uid not in study_cache:
            result = await db.execute(
                select(DicomStudy).where(
                    DicomStudy.institution_id == institution_id,
                    DicomStudy.study_instance_uid == study_uid,
                )
            )
            study = result.scalar_one_or_none()
            if not study:
                study = DicomStudy(
                    institution_id=institution_id,
                    study_instance_uid=study_uid,
                    patient_id=meta["patient_id"],
                    patient_name=meta["patient_name"],
                    study_date=meta["study_date"],
                    study_description=meta["study_description"],
                    modality=meta["modality"],
                    status="RECEIVING",
                    source_aet=source_aet,
                    storage_prefix=f"dicom/{institution_id}/{study_uid}",
                    dicom_metadata=meta.get("_raw_tags"),
                )
                db.add(study)
                await db.flush()
            study_cache[study_uid] = study
        study = study_cache[study_uid]

        # Get or create DicomSeries
        series_key = f"{study_uid}/{series_uid}"
        if series_key not in series_cache:
            result = await db.execute(
                select(DicomSeries).where(
                    DicomSeries.study_id == study.id,
                    DicomSeries.series_instance_uid == series_uid,
                )
            )
            series = result.scalar_one_or_none()
            if not series:
                series = DicomSeries(
                    study_id=study.id,
                    series_instance_uid=series_uid,
                    series_number=meta["series_number"],
                    series_description=meta["series_description"],
                    modality=meta["modality"],
                    storage_prefix=f"dicom/{institution_id}/{study_uid}/{series_uid}",
                )
                db.add(series)
                await db.flush()
            series_cache[series_key] = series
        series = series_cache[series_key]

        # Upload to Supabase
        try:
            await store_dicom_instance(study_uid, series_uid, sop_uid, dicom_bytes, institution_id)
        except Exception as exc:
            logger.error("Storage upload failed for %s: %s", sop_uid, exc)
            results.append(StowRsResult(
                study_instance_uid=study_uid,
                series_instance_uid=series_uid,
                sop_instance_uid=sop_uid,
                status="failure",
                reason=f"Storage error: {exc}",
            ))
            continue

        # Increment counters
        series.num_instances = (series.num_instances or 0) + 1
        study.num_instances = (study.num_instances or 0) + 1

        results.append(StowRsResult(
            study_instance_uid=study_uid,
            series_instance_uid=series_uid,
            sop_instance_uid=sop_uid,
            status="success",
        ))

    # Update study series count and status
    for study in study_cache.values():
        study.num_series = len([s for s in series_cache if s.startswith(study.study_instance_uid)])
        if study.status == "RECEIVING":
            study.status = "RECEIVED"

    await db.commit()

    success_count = sum(1 for r in results if r.status == "success")
    failure_count = len(results) - success_count

    return StowRsResponse(results=results, success_count=success_count, failure_count=failure_count)


# ─── WADO-RS (Retrieve / Worklist) ─────────────────────────────────────────

@router.get("/studies", response_model=DicomStudyList)
async def list_studies(
    user: Annotated[AuthenticatedUser, Depends(require_roles("ADMIN", "SERVICE_USER", "EXPERT"))],
    db: DbSession,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    modality: str | None = Query(None),
    study_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """WADO-RS: List studies (worklist) with optional filters."""
    q = select(DicomStudy).where(DicomStudy.institution_id == user.institution_id)
    if date_from:
        q = q.where(DicomStudy.study_date >= date_from)
    if date_to:
        q = q.where(DicomStudy.study_date <= date_to)
    if modality:
        q = q.where(DicomStudy.modality == modality.upper())
    if study_status:
        q = q.where(DicomStudy.status == study_status.upper())

    count_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_result.scalar_one()

    q = q.order_by(DicomStudy.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    studies = result.scalars().all()

    return DicomStudyList(items=[DicomStudyRead.model_validate(s) for s in studies], total=total)


@router.get("/studies/{study_uid}", response_model=DicomStudyRead)
async def get_study(
    study_uid: str,
    user: Annotated[AuthenticatedUser, Depends(require_roles("ADMIN", "SERVICE_USER", "EXPERT"))],
    db: DbSession,
):
    """WADO-RS: Get study metadata."""
    result = await db.execute(
        select(DicomStudy).where(
            DicomStudy.institution_id == user.institution_id,
            DicomStudy.study_instance_uid == study_uid,
        )
    )
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return DicomStudyRead.model_validate(study)


@router.get("/studies/{study_uid}/series")
async def list_series(
    study_uid: str,
    user: Annotated[AuthenticatedUser, Depends(require_roles("ADMIN", "SERVICE_USER", "EXPERT"))],
    db: DbSession,
):
    """WADO-RS: List series in a study."""
    result = await db.execute(
        select(DicomStudy).where(
            DicomStudy.institution_id == user.institution_id,
            DicomStudy.study_instance_uid == study_uid,
        )
    )
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    series_result = await db.execute(
        select(DicomSeries).where(DicomSeries.study_id == study.id)
    )
    series_list = series_result.scalars().all()
    return {"items": [s.__dict__ for s in series_list]}


@router.get("/worklist", response_model=DicomStudyList)
async def get_worklist(
    user: Annotated[AuthenticatedUser, Depends(require_roles("ADMIN", "SERVICE_USER", "EXPERT"))],
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get pending studies not yet linked to requests."""
    q = select(DicomStudy).where(
        DicomStudy.institution_id == user.institution_id,
        DicomStudy.request_id.is_(None),
        DicomStudy.status == "RECEIVED",
    )
    count_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = count_result.scalar_one()

    q = q.order_by(DicomStudy.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    studies = result.scalars().all()
    return DicomStudyList(items=[DicomStudyRead.model_validate(s) for s in studies], total=total)


# ─── Study Management ───────────────────────────────────────────────────────

@router.post("/studies/{study_uid}/link", response_model=DicomStudyRead)
async def link_study_to_request(
    study_uid: str,
    body: LinkStudyRequest,
    user: Annotated[AuthenticatedUser, Depends(require_roles("ADMIN"))],
    db: DbSession,
):
    """Link a DicomStudy to an existing Request."""
    result = await db.execute(
        select(DicomStudy).where(
            DicomStudy.institution_id == user.institution_id,
            DicomStudy.study_instance_uid == study_uid,
        )
    )
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    study.request_id = body.request_id
    study.status = "LINKED"
    await db.commit()
    await db.refresh(study)
    return DicomStudyRead.model_validate(study)


@router.post("/studies/{study_uid}/create-request", response_model=DicomStudyRead)
async def create_request_from_dicom_study(
    study_uid: str,
    body: CreateRequestFromStudyRequest,
    user: Annotated[AuthenticatedUser, Depends(require_roles("ADMIN", "SERVICE_USER"))],
    db: DbSession,
):
    """Auto-create a Request from a DICOM study."""
    result = await db.execute(
        select(DicomStudy).where(
            DicomStudy.institution_id == user.institution_id,
            DicomStudy.study_instance_uid == study_uid,
        )
    )
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")

    request = await create_request_from_study(
        study=study,
        service_id=body.service_id,
        institution_id=user.institution_id,
        user_id=user.id,
        db=db,
    )

    study.request_id = request.id
    study.status = "LINKED"
    await db.commit()
    await db.refresh(study)
    return DicomStudyRead.model_validate(study)
