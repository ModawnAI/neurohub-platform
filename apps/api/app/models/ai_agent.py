"""AI Agent Run model — tracks Gemini (or other LLM) invocations in the pipeline."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AIAgentRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ai_agent_runs"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="PRE_QC_REVIEW, REPORT_NARRATIVE, CLINICAL_SUMMARY, QC_ANOMALY",
    )
    model_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="gemini-3-flash-preview",
    )
    input_data: Mapped[dict | None] = mapped_column(JSONB)
    output_data: Mapped[dict | None] = mapped_column(JSONB)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    error_detail: Mapped[str | None] = mapped_column(Text)
