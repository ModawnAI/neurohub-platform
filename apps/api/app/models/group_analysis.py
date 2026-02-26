import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.request import Request
    from app.models.user import User


class GroupStudy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "group_studies"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    analysis_type: Mapped[str] = mapped_column(String(30), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB)
    result: Mapped[dict | None] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    members: Mapped[list["GroupStudyMember"]] = relationship(
        back_populates="study",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class GroupStudyMember(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "group_study_members"

    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_label: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    member_metadata: Mapped[dict | None] = mapped_column(JSONB)

    study: Mapped["GroupStudy"] = relationship(back_populates="members")
