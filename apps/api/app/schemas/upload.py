"""Schemas for file upload endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UploadPresignRequest(BaseModel):
    slot_name: str = Field(..., min_length=1, max_length=100)
    file_name: str = Field(..., min_length=1, max_length=500)
    content_type: str = Field(default="application/octet-stream", max_length=200)
    file_size: int = Field(..., gt=0)
    case_id: uuid.UUID | None = None  # Required for B2B uploads


class UploadPresignResponse(BaseModel):
    case_file_id: uuid.UUID
    presigned_url: str
    expires_at: datetime


class UploadCompleteRequest(BaseModel):
    checksum_sha256: str = Field(..., min_length=64, max_length=64)
    case_file_id: uuid.UUID | None = None  # Required for B2B uploads


class CaseFileRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    case_id: uuid.UUID
    slot_name: str
    file_name: str
    file_size: int | None = None
    content_type: str | None = None
    upload_status: str
    checksum_sha256: str | None = None
    created_at: datetime


class CaseFileListResponse(BaseModel):
    items: list[CaseFileRead]


class CaseRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    institution_id: uuid.UUID
    request_id: uuid.UUID
    patient_ref: str
    demographics: dict | None = None
    status: str
    created_at: datetime


class CaseListResponse(BaseModel):
    items: list[CaseRead]


class DownloadUrlResponse(BaseModel):
    url: str
    expires_at: datetime
