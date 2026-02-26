"""Pydantic schemas for feedback and learning loop."""
import uuid
from datetime import datetime, date

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    run_id: uuid.UUID
    evaluation_id: uuid.UUID | None = None
    feedback_type: str = Field(..., pattern="^(label_correction|false_positive|false_negative|quality_score|annotation)$")
    original_output: dict | None = None
    corrected_output: dict | None = None
    ground_truth: dict | None = None
    label_annotations: list[dict] | None = None
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    comments: str | None = None


class FeedbackRead(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    service_id: uuid.UUID
    feedback_type: str
    original_output: dict | None
    corrected_output: dict | None
    ground_truth: dict | None
    label_annotations: list[dict] | None
    quality_score: float | None
    comments: str | None
    included_in_training: bool
    created_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackStats(BaseModel):
    service_id: uuid.UUID
    total_feedback: int
    unused_feedback: int
    high_quality_feedback: int
    ready_for_training: bool
    threshold: int = 50


class TrainingJobCreate(BaseModel):
    trigger_type: str = "manual"
    hyperparameters: dict | None = None


class TrainingJobRead(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    trigger_type: str
    status: str
    feedback_count: int
    hyperparameters: dict | None
    training_metrics: dict | None
    started_at: datetime | None
    completed_at: datetime | None
    error_detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PerformanceMetricsRead(BaseModel):
    service_id: uuid.UUID
    artifact_id: uuid.UUID | None
    metric_date: date
    accuracy: float | None
    sensitivity: float | None
    specificity: float | None
    auc_roc: float | None
    f1_score: float | None
    avg_latency_s: float | None
    total_runs: int | None
    failure_rate: float | None
    expert_approval_rate: float | None
    evaluation_count: int | None
    computed_at: datetime

    model_config = {"from_attributes": True}


class PerformanceTimeSeries(BaseModel):
    service_id: uuid.UUID
    data_points: list[PerformanceMetricsRead]
