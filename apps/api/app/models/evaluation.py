import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ServiceEvaluator(UUIDMixin, TimestampMixin, Base):
    """Links evaluator users to services (many-to-many)."""

    __tablename__ = "service_evaluators"
    __table_args__ = (
        UniqueConstraint("service_id", "user_id", name="uq_service_evaluator"),
    )

    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Evaluation(UUIDMixin, TimestampMixin, Base):
    """Human-in-the-loop evaluation decisions (separate from medical QC)."""

    __tablename__ = "evaluations"

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
        index=True,
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="SET NULL"),
    )
    evaluator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    decision: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # APPROVE | REJECT | REVISION_NEEDED
    comments: Mapped[str | None] = mapped_column(Text)
    watermark_text: Mapped[str | None] = mapped_column(String(500))
    output_storage_path: Mapped[str | None] = mapped_column(String(1000))
