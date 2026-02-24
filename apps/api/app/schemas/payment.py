"""Pydantic schemas for Payment API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PaymentPrepare(BaseModel):
    service_id: uuid.UUID
    amount: float = Field(..., gt=0)
    request_id: uuid.UUID | None = None


class PaymentPrepareResponse(BaseModel):
    payment_id: uuid.UUID
    order_id: str
    amount: float
    currency: str = "KRW"
    customer_key: str


class PaymentConfirm(BaseModel):
    payment_key: str
    order_id: str
    amount: float = Field(..., gt=0)


class PaymentConfirmResponse(BaseModel):
    payment_id: uuid.UUID
    status: str
    method: str | None = None
    receipt_url: str | None = None


class PaymentRead(BaseModel):
    id: uuid.UUID
    order_id: str
    payment_key: str | None = None
    amount: float
    currency: str
    status: str
    method: str | None = None
    request_id: uuid.UUID | None = None
    confirmed_at: datetime | None = None
    created_at: datetime


class PaymentListResponse(BaseModel):
    items: list[PaymentRead]


class PaymentCancelRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
