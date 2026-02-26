"""DICOM Gateway service — parsing, storage, and study management."""

import logging
import struct
import uuid
from datetime import date
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("neurohub.dicom")

_STORAGE_BASE = f"{settings.supabase_url}/storage/v1" if settings.supabase_url else ""
DICOM_BUCKET = "dicom-files"

# ─── DICOM tag constants ────────────────────────────────────────────────────
TAG_STUDY_DATE = (0x0008, 0x0020)
TAG_STUDY_DESCRIPTION = (0x0008, 0x1030)
TAG_MODALITY = (0x0008, 0x0060)
TAG_SOP_INSTANCE_UID = (0x0008, 0x0018)
TAG_PATIENT_NAME = (0x0010, 0x0010)
TAG_PATIENT_ID = (0x0010, 0x0020)
TAG_STUDY_INSTANCE_UID = (0x0020, 0x000D)
TAG_SERIES_INSTANCE_UID = (0x0020, 0x000E)
TAG_SERIES_NUMBER = (0x0020, 0x0011)
TAG_SERIES_DESCRIPTION = (0x0008, 0x103E)

IMPLICIT_VR_TAGS: dict[tuple[int, int], str] = {
    TAG_STUDY_DATE: "DA",
    TAG_STUDY_DESCRIPTION: "LO",
    TAG_MODALITY: "CS",
    TAG_SOP_INSTANCE_UID: "UI",
    TAG_PATIENT_NAME: "PN",
    TAG_PATIENT_ID: "LO",
    TAG_STUDY_INSTANCE_UID: "UI",
    TAG_SERIES_INSTANCE_UID: "UI",
    TAG_SERIES_NUMBER: "IS",
    TAG_SERIES_DESCRIPTION: "LO",
}

EXPLICIT_VR_SHORT = {b"AE", b"AS", b"AT", b"CS", b"DA", b"DS", b"DT", b"FL",
                     b"FD", b"IS", b"LO", b"LT", b"PN", b"SH", b"SL", b"SS",
                     b"ST", b"TM", b"UI", b"UL", b"US"}


def _decode_value(raw: bytes, vr: str) -> str:
    try:
        return raw.decode("latin-1").rstrip("\x00").strip()
    except Exception:
        return ""


def get_dicom_metadata(dicom_bytes: bytes) -> dict[str, Any]:
    """Extract key DICOM tags from raw DICOM bytes (minimal parser).

    Returns a dict with keys: study_instance_uid, series_instance_uid,
    sop_instance_uid, patient_id, patient_name, study_date, study_description,
    modality, series_number, series_description.
    """
    if len(dicom_bytes) < 132:
        raise ValueError("File too short to be DICOM")
    if dicom_bytes[128:132] != b"DICM":
        raise ValueError("Missing DICM magic — not a valid DICOM file")

    pos = 132
    data = dicom_bytes
    n = len(data)
    tags: dict[tuple[int, int], bytes] = {}
    target_tags = set(IMPLICIT_VR_TAGS.keys())

    explicit_vr = True  # most modern DICOM is explicit little-endian

    while pos < n and len(tags) < len(target_tags):
        if pos + 4 > n:
            break
        try:
            group, elem = struct.unpack_from("<HH", data, pos)
        except struct.error:
            break
        pos += 4
        tag = (group, elem)

        if pos + 2 > n:
            break
        vr_bytes = data[pos: pos + 2]

        if vr_bytes in EXPLICIT_VR_SHORT:
            # Explicit VR short length
            pos += 2
            if pos + 2 > n:
                break
            length = struct.unpack_from("<H", data, pos)[0]
            pos += 2
        elif vr_bytes[:2].isalpha() and explicit_vr:
            # Explicit VR long length (OB, OW, SQ, UC, UN, UR, UT)
            pos += 2 + 2  # skip VR + reserved
            if pos + 4 > n:
                break
            length = struct.unpack_from("<I", data, pos)[0]
            pos += 4
        else:
            # Implicit VR
            if pos + 4 > n:
                break
            length = struct.unpack_from("<I", data, pos)[0]
            pos += 4

        if length == 0xFFFFFFFF:
            # undefined length — skip (we won't handle SQ deeply)
            break
        if pos + length > n:
            break

        if tag in target_tags:
            tags[tag] = data[pos: pos + length]
        pos += length

    def get_str(t: tuple[int, int]) -> str | None:
        raw = tags.get(t)
        if raw is None:
            return None
        vr = IMPLICIT_VR_TAGS.get(t, "LO")
        return _decode_value(raw, vr) or None

    study_date_raw = get_str(TAG_STUDY_DATE)
    study_date: date | None = None
    if study_date_raw and len(study_date_raw) == 8:
        try:
            study_date = date(int(study_date_raw[:4]), int(study_date_raw[4:6]), int(study_date_raw[6:8]))
        except ValueError:
            pass

    series_number_raw = get_str(TAG_SERIES_NUMBER)
    series_number: int | None = None
    if series_number_raw:
        try:
            series_number = int(series_number_raw)
        except ValueError:
            pass

    return {
        "study_instance_uid": get_str(TAG_STUDY_INSTANCE_UID) or "",
        "series_instance_uid": get_str(TAG_SERIES_INSTANCE_UID) or "",
        "sop_instance_uid": get_str(TAG_SOP_INSTANCE_UID) or "",
        "patient_id": get_str(TAG_PATIENT_ID) or "",
        "patient_name": get_str(TAG_PATIENT_NAME),
        "study_date": study_date,
        "study_description": get_str(TAG_STUDY_DESCRIPTION),
        "modality": get_str(TAG_MODALITY),
        "series_number": series_number,
        "series_description": get_str(TAG_SERIES_DESCRIPTION),
        # store raw tag values for metadata JSONB
        "_raw_tags": {f"{g:04X}{e:04X}": v.decode("latin-1", errors="replace")
                      for (g, e), v in tags.items()},
    }


def parse_dicom_multipart(body: bytes, content_type: str) -> list[bytes]:
    """Parse a multipart/related DICOM body into individual DICOM file bytes."""
    # Extract boundary from Content-Type header
    boundary: bytes | None = None
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("boundary="):
            boundary_str = part[len("boundary="):].strip().strip('"')
            boundary = boundary_str.encode()
            break

    if not boundary:
        raise ValueError("No boundary found in Content-Type")

    delimiter = b"--" + boundary
    parts = body.split(delimiter)
    dicom_files: list[bytes] = []

    for part in parts[1:]:  # skip preamble
        if part.strip() in (b"", b"--", b"--\r\n", b"\r\n--"):
            continue
        if part.startswith(b"--"):
            break  # end boundary
        # Split headers from body
        if b"\r\n\r\n" in part:
            _, payload = part.split(b"\r\n\r\n", 1)
        elif b"\n\n" in part:
            _, payload = part.split(b"\n\n", 1)
        else:
            continue
        # Strip trailing boundary delimiter cruft
        payload = payload.rstrip(b"\r\n")
        if payload:
            dicom_files.append(payload)

    return dicom_files


def _storage_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }


async def store_dicom_instance(
    study_uid: str,
    series_uid: str,
    sop_uid: str,
    dicom_bytes: bytes,
    institution_id: uuid.UUID,
) -> str:
    """Upload a DICOM instance to Supabase storage.

    Returns the storage path.
    """
    path = f"dicom/{institution_id}/{study_uid}/{series_uid}/{sop_uid}.dcm"
    url = f"{_STORAGE_BASE}/object/{DICOM_BUCKET}/{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            headers={**_storage_headers(), "Content-Type": "application/dicom"},
            content=dicom_bytes,
        )
        if resp.status_code not in (200, 201):
            # Try upsert
            resp2 = await client.put(
                url,
                headers={**_storage_headers(), "Content-Type": "application/dicom", "x-upsert": "true"},
                content=dicom_bytes,
            )
            resp2.raise_for_status()
    return path


async def create_request_from_study(
    study: Any,  # DicomStudy
    service_id: uuid.UUID,
    institution_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Any,
) -> Any:
    """Create a Request + Case + CaseFile records from a DicomStudy."""
    from sqlalchemy import select

    from app.models.request import Case, CaseFile, Request
    from app.models.service import PipelineDefinition, ServiceDefinition

    # Load service definition
    svc_result = await db.execute(
        select(ServiceDefinition).where(ServiceDefinition.id == service_id)
    )
    svc = svc_result.scalar_one_or_none()
    if not svc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Service not found")

    # Load pipeline
    pipeline_result = await db.execute(
        select(PipelineDefinition).where(PipelineDefinition.id == svc.pipeline_id)
    )
    pipeline = pipeline_result.scalar_one_or_none()

    request = Request(
        institution_id=institution_id,
        service_id=service_id,
        pipeline_id=svc.pipeline_id,
        service_snapshot=svc.__dict__ if hasattr(svc, "__dict__") else {},
        pipeline_snapshot=pipeline.__dict__ if pipeline and hasattr(pipeline, "__dict__") else {},
        status="CREATED",
        requested_by=user_id,
        inputs={"dicom_study_id": str(study.id), "study_instance_uid": study.study_instance_uid},
    )
    db.add(request)
    await db.flush()

    case = Case(
        institution_id=institution_id,
        request_id=request.id,
        patient_ref=study.patient_id or "UNKNOWN",
        demographics={
            "patient_name": study.patient_name,
            "patient_id": study.patient_id,
            "study_date": study.study_date.isoformat() if study.study_date else None,
        },
        status="CREATED",
    )
    db.add(case)
    await db.flush()

    # Create CaseFile records for each DICOM series
    for series in study.series:
        path = series.storage_prefix or f"dicom/{institution_id}/{study.study_instance_uid}/{series.series_instance_uid}"
        cf = CaseFile(
            institution_id=institution_id,
            case_id=case.id,
            slot_name=f"series_{series.series_number or 0}",
            file_name=f"series_{series.series_instance_uid}",
            content_type="application/dicom",
            storage_path=path,
            upload_status="COMPLETED",
        )
        db.add(cf)

    await db.flush()
    return request
