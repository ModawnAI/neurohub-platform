import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.request import RequestRead


class QCDecisionCreate(BaseModel):
    decision: str = Field(..., pattern="^(APPROVE|REJECT|RERUN)$")
    qc_score: float | None = Field(default=None, ge=0, le=100)
    comments: str | None = Field(default=None, max_length=5000)


class ReportReviewCreate(BaseModel):
    decision: str = Field(..., pattern="^(APPROVE|REVISION_NEEDED)$")
    comments: str | None = Field(default=None, max_length=5000)


class ReviewQueueItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    service_name: str | None = None
    service_display_name: str | None = None
    status: str
    case_count: int = 0
    priority: int = 5
    requested_by: uuid.UUID | None = None
    institution_id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None = None


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int


class ReviewDetail(BaseModel):
    request: RequestRead
    cases: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    qc_decisions: list[dict[str, Any]] = []
    report_reviews: list[dict[str, Any]] = []
