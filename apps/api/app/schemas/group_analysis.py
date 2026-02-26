import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class GroupStudyCreate(BaseModel):
    name: str
    description: str | None = None
    service_id: uuid.UUID
    analysis_type: str  # COMPARISON | REGRESSION | CORRELATION | LONGITUDINAL
    config: dict[str, Any] | None = None


class GroupStudyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None


class GroupStudyMemberRead(BaseModel):
    id: uuid.UUID
    study_id: uuid.UUID
    request_id: uuid.UUID
    group_label: str
    member_metadata: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GroupStudyRead(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    name: str
    description: str | None
    service_id: uuid.UUID
    status: str
    analysis_type: str
    config: dict[str, Any] | None
    result: dict[str, Any] | None
    created_by: uuid.UUID | None
    members: list[GroupStudyMemberRead]
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class GroupStudyBrief(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    service_id: uuid.UUID
    status: str
    analysis_type: str
    member_count: int
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class AddMemberRequest(BaseModel):
    request_id: uuid.UUID
    group_label: str = "default"
    member_metadata: dict[str, Any] | None = None


class GroupMetrics(BaseModel):
    mean: float | None
    std: float | None
    n: int


class GroupSummary(BaseModel):
    label: str
    n: int
    metrics: dict[str, GroupMetrics]


class StatisticalTest(BaseModel):
    name: str
    p_value: float | None
    effect_size: float | None
    statistic: float | None = None


class GroupStudyResult(BaseModel):
    summary: dict[str, Any]
    groups: list[GroupSummary]
    statistical_tests: list[StatisticalTest]
