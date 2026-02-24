import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Payment(UUIDMixin, TimestampMixin, Base):
    """Toss Payments transaction records."""

    __tablename__ = "payments"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="SET NULL"),
    )
    order_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    payment_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="KRW")
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )  # PENDING | CONFIRMED | FAILED | CANCELLED | REFUNDED
    method: Mapped[str | None] = mapped_column(String(50))
    toss_response: Mapped[dict | None] = mapped_column(JSONB)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_detail: Mapped[str | None] = mapped_column(Text)
