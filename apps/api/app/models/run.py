import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.request import Case, Request


class Run(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "runs"

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
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    job_spec: Mapped[dict | None] = mapped_column(JSONB)
    result_manifest: Mapped[dict | None] = mapped_column(JSONB)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    cost_amount: Mapped[float | None] = mapped_column(Numeric(18, 6))
    worker_id: Mapped[str | None] = mapped_column(String(200))
    celery_task_id: Mapped[str | None] = mapped_column(String(200))
    progress_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    current_step: Mapped[str | None] = mapped_column(String(200))
    output_data: Mapped[dict | None] = mapped_column(JSONB)
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_detail: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    request: Mapped["Request"] = relationship(back_populates="runs")
    case: Mapped["Case"] = relationship(lazy="selectin")
    steps: Mapped[list["RunStep"]] = relationship(
        back_populates="run",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="RunStep.step_index",
    )


class RunStep(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "run_steps"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    docker_image: Mapped[str | None] = mapped_column(String(500))
    input_artifacts: Mapped[dict | None] = mapped_column(JSONB)
    output_artifacts: Mapped[dict | None] = mapped_column(JSONB)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    logs_tail: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_detail: Mapped[str | None] = mapped_column(Text)

    run: Mapped["Run"] = relationship(back_populates="steps")
