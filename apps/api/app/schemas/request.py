import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RequestStatus(StrEnum):
    CREATED = "CREATED"
    RECEIVING = "RECEIVING"
    STAGING = "STAGING"
    READY_TO_COMPUTE = "READY_TO_COMPUTE"
    COMPUTING = "COMPUTING"
    QC = "QC"
    REPORTING = "REPORTING"
    EXPERT_REVIEW = "EXPERT_REVIEW"
    FINAL = "FINAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CaseStatus(StrEnum):
    CREATED = "CREATED"
    RECEIVING = "RECEIVING"
    READY = "READY"


class CaseCreate(BaseModel):
    patient_ref: str = Field(..., min_length=1, max_length=100)
    demographics: dict[str, Any] | None = None


class RequestCreate(BaseModel):
    service_id: uuid.UUID
    pipeline_id: uuid.UUID
    inputs: dict[str, Any] | None = None
    options: dict[str, Any] | None = None
    priority: int = Field(default=5, ge=1, le=10)
    cases: list[CaseCreate] = Field(..., min_length=1)
    idempotency_key: str | None = Field(default=None, max_length=120)


class RequestRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    institution_id: uuid.UUID
    service_id: uuid.UUID
    pipeline_id: uuid.UUID
    status: RequestStatus
    priority: int
    inputs: dict[str, Any] | None = None
    options: dict[str, Any] | None = None
    requested_by: uuid.UUID | None = None
    department: str | None = None
    error_detail: str | None = None
    cancel_reason: str | None = None
    idempotency_key: str | None = None
    service_snapshot: dict[str, Any] | None = None
    pipeline_snapshot: dict[str, Any] | None = None
    case_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None


class RequestListResponse(BaseModel):
    items: list[RequestRead]
    total: int


class ConfirmRequest(BaseModel):
    confirm_note: str | None = Field(default=None, max_length=1000)


class CancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class TransitionRequest(BaseModel):
    target_status: RequestStatus
    note: str | None = Field(default=None, max_length=2000)

