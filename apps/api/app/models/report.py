import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Report(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="GENERATING")
    title: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[dict | None] = mapped_column(JSONB)
    summary: Mapped[str | None] = mapped_column(Text)
    pdf_storage_path: Mapped[str | None] = mapped_column(String(1000))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    watermarked_storage_path: Mapped[str | None] = mapped_column(String(1000))
    celery_task_id: Mapped[str | None] = mapped_column(String(200))
    error_detail: Mapped[str | None] = mapped_column(Text)


class ReportReview(UUIDMixin, Base):
    __tablename__ = "report_reviews"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text)
    # Structured findings for expert reviews
    severity: Mapped[str | None] = mapped_column(String(20))  # LOW, MEDIUM, HIGH, CRITICAL
    category: Mapped[str | None] = mapped_column(String(50))  # ARTIFACT, MOTION, QUALITY, CLINICAL
    recommendation: Mapped[str | None] = mapped_column(Text)
    findings: Mapped[dict | None] = mapped_column(JSONB)  # Flexible structured data
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ReviewAssignment(UUIDMixin, Base):
    """Tracks reviewer assignments for multi-reviewer workflow."""

    __tablename__ = "review_assignments"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING"
    )  # PENDING, COMPLETED, DECLINED
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
