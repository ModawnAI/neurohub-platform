"""DICOM Service — pydicom-based metadata extraction, multipart parsing, and NIfTI conversion."""

import io
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from datetime import date

import pydicom
import pydicom.errors

import httpx

from app.config import settings

logger = logging.getLogger("neurohub.dicom")


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def get_dicom_metadata(dicom_bytes: bytes) -> dict:
    """Parse DICOM bytes with pydicom and return a structured metadata dict."""
    ds = pydicom.dcmread(io.BytesIO(dicom_bytes), stop_before_pixels=True)

    def tag(attr, default=None):
        try:
            val = getattr(ds, attr, None)
            if val is None:
                return default
            return str(val).strip() or default
        except Exception:
            return default

    # Parse study date
    study_date = None
    raw_date = tag("StudyDate")
    if raw_date and len(raw_date) == 8:
        try:
            study_date = date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8]))
        except ValueError:
            pass

    # Parse series number
    series_number = None
    try:
        series_number = int(ds.SeriesNumber) if hasattr(ds, "SeriesNumber") else None
    except (ValueError, TypeError):
        pass

    # Build full metadata dict (all tags as JSON-serializable dict)
    metadata: dict[str, str] = {}
    for elem in ds:
        try:
            if elem.tag.group == 0x7FE0:  # skip pixel data
                continue
            metadata[str(elem.tag)] = str(elem.value)[:200]
        except Exception:
            pass

    return {
        "study_instance_uid": tag("StudyInstanceUID") or "",
        "series_instance_uid": tag("SeriesInstanceUID") or "",
        "sop_instance_uid": tag("SOPInstanceUID") or "",
        "patient_id": tag("PatientID") or "",
        "patient_name": tag("PatientName"),
        "study_date": study_date,
        "study_description": tag("StudyDescription"),
        "modality": tag("Modality"),
        "series_number": series_number,
        "series_description": tag("SeriesDescription"),
        "_raw_tags": metadata,
    }


# ---------------------------------------------------------------------------
# Multipart DICOM parsing
# ---------------------------------------------------------------------------

def parse_dicom_multipart(body: bytes, content_type: str) -> list[bytes]:
    """Parse a multipart/related DICOM body and return a list of DICOM instance bytes.

    Each part is validated with pydicom before being included.
    """
    # Extract boundary from content_type header
    boundary: bytes | None = None
    for part in content_type.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part[len("boundary="):].strip('"').encode()
            break

    if boundary is None:
        raise ValueError(f"No boundary found in Content-Type: {content_type}")

    delimiter = b"--" + boundary
    parts: list[bytes] = []

    segments = body.split(delimiter)
    for segment in segments:
        # Skip preamble and epilogue
        if segment in (b"", b"--", b"--\r\n"):
            continue
        if segment.startswith(b"--"):
            continue

        # Strip leading CRLF
        if segment.startswith(b"\r\n"):
            segment = segment[2:]

        # Separate headers from body
        if b"\r\n\r\n" in segment:
            _, instance_body = segment.split(b"\r\n\r\n", 1)
        else:
            instance_body = segment

        # Strip trailing CRLF
        instance_body = instance_body.rstrip(b"\r\n")

        if not instance_body:
            continue

        # Validate with pydicom
        try:
            pydicom.dcmread(io.BytesIO(instance_body), stop_before_pixels=True)
            parts.append(instance_body)
        except pydicom.errors.InvalidDicomError:
            logger.warning("Skipping invalid DICOM part (%d bytes)", len(instance_body))

    return parts


# ---------------------------------------------------------------------------
# Storage helpers (Supabase)
# ---------------------------------------------------------------------------

async def _download_from_storage(storage_path: str) -> bytes:
    """Download a file from Supabase Storage using the service role key."""
    bucket = settings.storage_bucket_inputs
    url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{storage_path}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.content


# ---------------------------------------------------------------------------
# store_dicom_instance — placeholder (wired up by STOW-RS / SCP callers)
# ---------------------------------------------------------------------------

async def store_dicom_instance(
    dicom_bytes: bytes,
    institution_id: uuid.UUID,
    *,
    received_via: str = "STOW_RS",
    source_ae_title: str | None = None,
) -> dict:
    """Persist a DICOM instance to Supabase Storage and return the storage path + metadata."""
    meta = get_dicom_metadata(dicom_bytes)
    sop_uid = meta["sop_instance_uid"] or str(uuid.uuid4())
    storage_path = f"{institution_id}/dicom/{meta['study_instance_uid']}/{meta['series_instance_uid']}/{sop_uid}.dcm"

    # Upload to Supabase
    bucket = settings.storage_bucket_inputs
    upload_url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{storage_path}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
        "Content-Type": "application/octet-stream",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(upload_url, headers=headers, content=dicom_bytes)
        resp.raise_for_status()

    return {
        "storage_path": storage_path,
        "metadata": meta,
        "received_via": received_via,
        "source_ae_title": source_ae_title,
    }


async def create_request_from_study(
    study_instance_uid: str,
    institution_id: uuid.UUID,
    service_id: uuid.UUID | None = None,
) -> dict:
    """Create an analysis Request from an already-stored DICOM study (stub)."""
    # Actual DB creation is handled by the router layer; this assembles the payload.
    return {
        "study_instance_uid": study_instance_uid,
        "institution_id": str(institution_id),
        "service_id": str(service_id) if service_id else None,
        "source": "dicom_gateway",
    }


# ---------------------------------------------------------------------------
# DICOM → NIfTI conversion
# ---------------------------------------------------------------------------

async def convert_dicom_series_to_nifti(
    series_paths: list[str],
    output_dir: str,
    institution_id: uuid.UUID,
) -> list[str]:
    """Download DICOM files from Supabase Storage and convert to NIfTI using dcm2niix.

    Returns list of NIfTI file paths written to *output_dir*.
    Raises RuntimeError if dcm2niix is not installed (graceful degradation).
    """
    dcm2niix = shutil.which("dcm2niix")
    if dcm2niix is None:
        raise RuntimeError(
            "dcm2niix is not installed or not on PATH. "
            "Install via: brew install dcm2niix  |  apt install dcm2niix"
        )

    with tempfile.TemporaryDirectory(prefix="neurohub_dcm_") as dcm_dir:
        # Download each DICOM file into the temp dir
        for storage_path in series_paths:
            filename = os.path.basename(storage_path) or f"{uuid.uuid4()}.dcm"
            local_path = os.path.join(dcm_dir, filename)
            data = await _download_from_storage(storage_path)
            with open(local_path, "wb") as fh:
                fh.write(data)

        os.makedirs(output_dir, exist_ok=True)

        cmd = [
            dcm2niix,
            "-z", "y",          # gzip NIfTI
            "-f", "%p_%s",      # filename pattern
            "-o", output_dir,
            dcm_dir,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            logger.error("dcm2niix failed: %s", result.stderr)
            raise RuntimeError(f"dcm2niix conversion failed: {result.stderr[:500]}")

        logger.info("dcm2niix output: %s", result.stdout[:500])

    # Collect generated NIfTI files
    nifti_files = [
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.endswith(".nii.gz") or f.endswith(".nii")
    ]
    return nifti_files
