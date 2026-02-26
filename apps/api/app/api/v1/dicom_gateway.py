"""DICOM Gateway API — STOW-RS ingestion + DICOM SCP management endpoints."""

import uuid
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.security.supabase_jwt import require_auth

logger = logging.getLogger("neurohub.dicom_gateway")

router = APIRouter(prefix="/dicom", tags=["dicom"])


# ---------------------------------------------------------------------------
# Dependency: require admin scope
# ---------------------------------------------------------------------------

async def require_admin(user=Depends(require_auth)):
    """Ensure the authenticated user has admin privileges."""
    role = (user.get("user_metadata") or {}).get("role", "")
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


# ---------------------------------------------------------------------------
# STOW-RS: POST /dicom/studies
# ---------------------------------------------------------------------------

@router.post("/studies", status_code=status.HTTP_200_OK)
async def stow_rs_store(request: Request, user=Depends(require_auth)):
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
async def scp_status_endpoint(user=Depends(require_auth)):
    """Get current DICOM SCP status (running/stopped, port, AE title)."""
    from app.services import pacs_service

    return pacs_service.get_scp_status()
