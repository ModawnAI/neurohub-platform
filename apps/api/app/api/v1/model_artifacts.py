"""Model artifact management endpoints."""
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select

from app.config import settings
from app.dependencies import AuthenticatedUser, CurrentUser, DbSession, require_roles
from app.models.model_artifact import ModelArtifact
from app.models.service import ServiceDefinition
from app.schemas.model_artifact import (
    ArtifactApproveRequest,
    ArtifactRejectRequest,
    ModelArtifactList,
    ModelArtifactRead,
)

router = APIRouter(tags=["Model Artifacts"])
logger = logging.getLogger("neurohub.model_artifacts")

ALLOWED_ARTIFACT_TYPES = {"weights", "script", "requirements", "dockerfile", "config", "test_data"}
ALLOWED_EXTENSIONS = {
    "weights": {".pt", ".pth", ".onnx", ".h5", ".pkl", ".joblib", ".bin", ".safetensors"},
    "script": {".py"},
    "requirements": {".txt"},
    "dockerfile": {""},
    "config": {".json", ".yaml", ".yml"},
    "test_data": {".json", ".nii", ".nii.gz", ".dcm", ".csv"},
}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB


@router.post("/model-artifacts/upload", response_model=ModelArtifactRead, status_code=201)
async def upload_artifact(
    service_id: Annotated[uuid.UUID, Form()],
    artifact_type: Annotated[str, Form()],
    db: DbSession,
    user: CurrentUser = Depends(require_roles("EXPERT", "ADMIN")),
    runtime: Annotated[str | None, Form()] = None,
    file: UploadFile = File(...),
):
    """Upload a model artifact (script, weights, requirements, etc.)."""
    if artifact_type not in ALLOWED_ARTIFACT_TYPES:
        raise HTTPException(400, f"Invalid artifact_type. Allowed: {ALLOWED_ARTIFACT_TYPES}")

    svc = await db.get(ServiceDefinition, service_id)
    if not svc or svc.institution_id != user.institution_id:
        raise HTTPException(404, "Service not found")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large (max 2GB)")

    checksum = hashlib.sha256(content).hexdigest()
    storage_path = f"{user.institution_id}/{service_id}/{uuid.uuid4()}/{file.filename}"

    from app.services.storage import put_object

    await put_object(
        "model-artifacts",
        storage_path,
        content,
        content_type=file.content_type or "application/octet-stream",
    )

    artifact = ModelArtifact(
        institution_id=user.institution_id,
        service_id=service_id,
        created_by=user.id,
        artifact_type=artifact_type,
        file_name=file.filename or "unknown",
        file_size=len(content),
        checksum_sha256=checksum,
        storage_path=storage_path,
        content_type=file.content_type,
        runtime=runtime,
        status="PENDING_SCAN",
    )
    db.add(artifact)
    await db.flush()
    await db.refresh(artifact)
    await db.commit()

    from app.worker.model_tasks import scan_artifact
    scan_artifact.delay(str(artifact.id))

    return ModelArtifactRead.model_validate(artifact)


@router.get("/services/{service_id}/artifacts", response_model=ModelArtifactList)
async def list_artifacts(
    service_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    """List all artifacts for a service."""
    result = await db.execute(
        select(ModelArtifact)
        .where(
            ModelArtifact.service_id == service_id,
            ModelArtifact.institution_id == user.institution_id,
        )
        .order_by(ModelArtifact.created_at.desc())
    )
    items = result.scalars().all()
    return ModelArtifactList(
        items=[ModelArtifactRead.model_validate(a) for a in items],
        total=len(items),
    )


@router.get("/model-artifacts/{artifact_id}", response_model=ModelArtifactRead)
async def get_artifact(artifact_id: uuid.UUID, db: DbSession, user: AuthenticatedUser):
    artifact = await db.get(ModelArtifact, artifact_id)
    if not artifact or artifact.institution_id != user.institution_id:
        raise HTTPException(404, "Artifact not found")
    return ModelArtifactRead.model_validate(artifact)


@router.post("/model-artifacts/{artifact_id}/approve", response_model=ModelArtifactRead)
async def approve_artifact(
    artifact_id: uuid.UUID,
    body: ArtifactApproveRequest,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """Admin: approve artifact and optionally trigger Docker image build."""
    artifact = await db.get(ModelArtifact, artifact_id)
    if not artifact or artifact.institution_id != user.institution_id:
        raise HTTPException(404, "Artifact not found")
    if artifact.status not in ("PENDING_SCAN", "APPROVED", "FLAGGED"):
        raise HTTPException(400, f"Cannot approve artifact in status: {artifact.status}")

    artifact.status = "APPROVED"
    artifact.reviewed_by = user.id
    artifact.review_notes = body.review_notes
    artifact.reviewed_at = datetime.now(timezone.utc)

    if body.trigger_build and artifact.artifact_type in ("script", "weights"):
        artifact.build_status = "PENDING"

    await db.commit()
    await db.refresh(artifact)

    if body.trigger_build and artifact.artifact_type in ("script", "weights"):
        from app.worker.model_tasks import build_service_image
        build_service_image.delay(str(artifact.id))

    return ModelArtifactRead.model_validate(artifact)


@router.post("/model-artifacts/{artifact_id}/reject", response_model=ModelArtifactRead)
async def reject_artifact(
    artifact_id: uuid.UUID,
    body: ArtifactRejectRequest,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    artifact = await db.get(ModelArtifact, artifact_id)
    if not artifact or artifact.institution_id != user.institution_id:
        raise HTTPException(404, "Artifact not found")

    artifact.status = "REJECTED"
    artifact.reviewed_by = user.id
    artifact.review_notes = body.review_notes
    artifact.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(artifact)
    return ModelArtifactRead.model_validate(artifact)


@router.delete("/model-artifacts/{artifact_id}", status_code=204)
async def delete_artifact(
    artifact_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    artifact = await db.get(ModelArtifact, artifact_id)
    if not artifact or artifact.institution_id != user.institution_id:
        raise HTTPException(404, "Artifact not found")
    if artifact.status not in ("PENDING_SCAN", "REJECTED"):
        raise HTTPException(400, "Can only delete PENDING_SCAN or REJECTED artifacts")
    await db.delete(artifact)
    await db.commit()
