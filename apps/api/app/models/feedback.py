"""Feedback and learning loop ORM models."""
import uuid
from datetime import datetime, date

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ModelFeedback(UUIDMixin, Base):
    __tablename__ = "model_feedback"

    institution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False, index=True)
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="SET NULL"))
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("service_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_type: Mapped[str] = mapped_column(String(30), nullable=False)
    original_output: Mapped[dict | None] = mapped_column(JSONB)
    corrected_output: Mapped[dict | None] = mapped_column(JSONB)
    ground_truth: Mapped[dict | None] = mapped_column(JSONB)
    label_annotations: Mapped[list | None] = mapped_column(JSONB)
    quality_score: Mapped[float | None] = mapped_column(Float)
    comments: Mapped[str | None] = mapped_column(Text)
    included_in_training: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    training_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelTrainingJob(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "model_training_jobs"

    institution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False, index=True)
    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("service_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    base_artifact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    result_artifact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    feedback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feedback_ids: Mapped[list | None] = mapped_column(JSONB)
    hyperparameters: Mapped[dict | None] = mapped_column(JSONB)
    training_metrics: Mapped[dict | None] = mapped_column(JSONB)
    celery_task_id: Mapped[str | None] = mapped_column(String(200))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_detail: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))


class ModelPerformanceMetrics(UUIDMixin, Base):
    __tablename__ = "model_performance_metrics"

    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("service_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    accuracy: Mapped[float | None] = mapped_column(Float)
    sensitivity: Mapped[float | None] = mapped_column(Float)
    specificity: Mapped[float | None] = mapped_column(Float)
    auc_roc: Mapped[float | None] = mapped_column(Float)
    f1_score: Mapped[float | None] = mapped_column(Float)
    mae: Mapped[float | None] = mapped_column(Float)
    rmse: Mapped[float | None] = mapped_column(Float)
    avg_latency_s: Mapped[float | None] = mapped_column(Float)
    p95_latency_s: Mapped[float | None] = mapped_column(Float)
    total_runs: Mapped[int | None] = mapped_column(Integer)
    failure_rate: Mapped[float | None] = mapped_column(Float)
    expert_approval_rate: Mapped[float | None] = mapped_column(Float)
    evaluation_count: Mapped[int | None] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
