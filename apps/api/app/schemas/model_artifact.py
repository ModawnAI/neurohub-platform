"""Pydantic schemas for model artifacts."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CodeSecurityScanRead(BaseModel):
    id: uuid.UUID
    scanner: str
    status: str
    severity: str | None
    findings: list[dict] | None
    scanned_at: datetime

    model_config = {"from_attributes": True}


class ModelArtifactRead(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    artifact_type: str
    file_name: str
    file_size: int | None
    checksum_sha256: str | None
    runtime: str | None
    status: str
    container_image: str | None
    build_status: str | None
    review_notes: str | None
    reviewed_at: datetime | None
    security_scans: list[CodeSecurityScanRead] = []
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class ModelArtifactList(BaseModel):
    items: list[ModelArtifactRead]
    total: int


class ArtifactApproveRequest(BaseModel):
    review_notes: str | None = None
    trigger_build: bool = True


class ArtifactRejectRequest(BaseModel):
    review_notes: str = Field(..., min_length=10)
