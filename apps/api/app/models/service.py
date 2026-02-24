import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ServiceDefinition(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "service_definitions"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version_legacy: Mapped[str] = mapped_column(String(30), nullable=False, default="1.0.0")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    version_label: Mapped[str] = mapped_column(String(30), nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    department: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(100))

    # --- Structured JSON fields ---
    input_schema: Mapped[dict | None] = mapped_column(JSONB, comment="Demographics/input fields")
    upload_slots: Mapped[list | None] = mapped_column(JSONB, comment="File upload slot definitions")
    options_schema: Mapped[dict | None] = mapped_column(
        JSONB, comment="Configurable analysis options"
    )
    pricing: Mapped[dict | None] = mapped_column(JSONB, comment="Pricing structure")
    output_schema: Mapped[dict | None] = mapped_column(JSONB, comment="Expected output structure")

    # Legacy field kept for backward compat (will be removed)
    inputs_schema: Mapped[dict | None] = mapped_column(JSONB)

    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parent_service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_definitions.id", ondelete="SET NULL"),
    )

    # --- Evaluation / service type fields ---
    service_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="AUTOMATIC"
    )  # AUTOMATIC | HUMAN_IN_LOOP
    requires_evaluator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    pipelines: Mapped[list["PipelineDefinition"]] = relationship(
        back_populates="service",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class PipelineDefinition(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "pipeline_definitions"

    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False, default="1.0.0")
    steps: Mapped[list | None] = mapped_column(JSONB)
    qc_rules: Mapped[dict | None] = mapped_column(JSONB)
    resource_requirements: Mapped[dict | None] = mapped_column(JSONB)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    service: Mapped["ServiceDefinition"] = relationship(back_populates="pipelines")
