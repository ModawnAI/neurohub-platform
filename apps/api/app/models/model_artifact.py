"""Model artifact ORM models."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ModelArtifact(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "model_artifacts"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    artifact_type: Mapped[str] = mapped_column(String(30), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    content_type: Mapped[str | None] = mapped_column(String(100))
    runtime: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING_SCAN")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    review_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    container_image: Mapped[str | None] = mapped_column(String(500))
    container_image_digest: Mapped[str | None] = mapped_column(String(100))
    build_status: Mapped[str | None] = mapped_column(String(20))
    build_log: Mapped[str | None] = mapped_column(Text)

    security_scans: Mapped[list["CodeSecurityScan"]] = relationship(
        back_populates="artifact", lazy="selectin", cascade="all, delete-orphan"
    )


class CodeSecurityScan(UUIDMixin, Base):
    __tablename__ = "code_security_scans"

    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_artifacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scanner: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(10))
    findings: Mapped[list | None] = mapped_column(JSONB)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    artifact: Mapped["ModelArtifact"] = relationship(back_populates="security_scans")
