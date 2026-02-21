import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.run import Run


class Request(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "requests"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    current_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    service_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    pipeline_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CREATED")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    inputs: Mapped[dict | None] = mapped_column(JSONB)
    options: Mapped[dict | None] = mapped_column(JSONB)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    department: Mapped[str | None] = mapped_column(String(100))
    error_detail: Mapped[str | None] = mapped_column(Text)
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), unique=True)

    cases: Mapped[list["Case"]] = relationship(
        back_populates="request",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    runs: Mapped[list["Run"]] = relationship(
        back_populates="request",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class Case(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cases"

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
    )
    patient_ref: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    demographics: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CREATED")

    request: Mapped["Request"] = relationship(back_populates="cases")
    files: Mapped[list["CaseFile"]] = relationship(
        back_populates="case",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class CaseFile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "case_files"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_name: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    content_type: Mapped[str | None] = mapped_column(String(200))
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    upload_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")

    case: Mapped["Case"] = relationship(back_populates="files")
    upload_session: Mapped["UploadSession | None"] = relationship(
        back_populates="case_file",
        lazy="selectin",
        uselist=False,
    )


class UploadSession(UUIDMixin, Base):
    __tablename__ = "upload_sessions"

    case_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    presigned_url: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    case_file: Mapped["CaseFile"] = relationship(back_populates="upload_session")
