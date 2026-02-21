import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
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
    version: Mapped[str] = mapped_column(String(30), nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    department: Mapped[str | None] = mapped_column(String(100))
    inputs_schema: Mapped[dict | None] = mapped_column(JSONB)
    options_schema: Mapped[dict | None] = mapped_column(JSONB)
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

