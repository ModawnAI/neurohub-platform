"""DICOM Study and Series models for the DICOM Gateway."""

import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DicomStudy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "dicom_studies"
    __table_args__ = (
        UniqueConstraint("institution_id", "study_instance_uid", name="uq_dicom_study_institution_uid"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    study_instance_uid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    patient_name: Mapped[str | None] = mapped_column(String(500))
    study_date: Mapped[date | None] = mapped_column(Date)
    study_description: Mapped[str | None] = mapped_column(String(500))
    modality: Mapped[str | None] = mapped_column(String(20))
    num_series: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    num_instances: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_prefix: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RECEIVING", index=True)
    source_aet: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    dicom_metadata: Mapped[dict | None] = mapped_column(JSONB)

    series: Mapped[list["DicomSeries"]] = relationship(
        back_populates="study",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class DicomSeries(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "dicom_series"

    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dicom_studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    series_instance_uid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    series_number: Mapped[int | None] = mapped_column(Integer)
    series_description: Mapped[str | None] = mapped_column(String(500))
    modality: Mapped[str | None] = mapped_column(String(20))
    num_instances: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_prefix: Mapped[str | None] = mapped_column(String(1000))

    study: Mapped["DicomStudy"] = relationship(back_populates="series")
