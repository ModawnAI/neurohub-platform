"""Pydantic schemas for Evaluation API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EvaluationCreate(BaseModel):
    decision: str = Field(..., pattern="^(APPROVE|REJECT|REVISION_NEEDED)$")
    comments: str | None = None
    watermark_text: str | None = None


class EvaluationRead(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    request_id: uuid.UUID
    run_id: uuid.UUID | None = None
    evaluator_id: uuid.UUID | None = None
    decision: str
    comments: str | None = None
    watermark_text: str | None = None
    output_storage_path: str | None = None
    created_at: datetime


class EvaluationQueueItem(BaseModel):
    request_id: uuid.UUID
    request_status: str
    service_name: str
    service_display_name: str
    case_count: int
    created_at: datetime
    priority: str


class EvaluationQueueResponse(BaseModel):
    items: list[EvaluationQueueItem]


class EvaluationDetailResponse(BaseModel):
    request_id: uuid.UUID
    request_status: str
    service_name: str
    service_display_name: str
    cases: list[dict]
    files: list[dict]
    runs: list[dict]
    evaluations: list[EvaluationRead]


class ServiceEvaluatorCreate(BaseModel):
    user_id: uuid.UUID


class ServiceEvaluatorRead(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    user_id: uuid.UUID
    institution_id: uuid.UUID
    is_active: bool
    created_at: datetime


class ServiceEvaluatorListResponse(BaseModel):
    items: list[ServiceEvaluatorRead]
