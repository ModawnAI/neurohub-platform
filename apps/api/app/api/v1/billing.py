"""Billing and usage ledger endpoints."""

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.dependencies import AuthenticatedUser, DbSession
from app.models.billing import UsageLedger

router = APIRouter(tags=["Billing"])


class UsageSummaryItem(BaseModel):
    service_id: uuid.UUID | None
    service_version: str | None
    charge_type: str
    total_units: int
    total_amount: float
    currency: str


class UsageSummary(BaseModel):
    items: list[UsageSummaryItem]
    start_date: date
    end_date: date


@router.get("/billing/usage", response_model=UsageSummary)
async def get_usage_summary(
    db: DbSession,
    user: AuthenticatedUser,
    start_date: date = Query(...),
    end_date: date = Query(...),
):
    result = await db.execute(
        select(
            UsageLedger.service_id,
            UsageLedger.service_version,
            UsageLedger.charge_type,
            func.sum(UsageLedger.units).label("total_units"),
            func.sum(UsageLedger.amount).label("total_amount"),
            UsageLedger.currency,
        )
        .where(
            UsageLedger.institution_id == user.institution_id,
            UsageLedger.created_at >= datetime.combine(start_date, datetime.min.time()),
            UsageLedger.created_at <= datetime.combine(end_date, datetime.max.time()),
        )
        .group_by(
            UsageLedger.service_id,
            UsageLedger.service_version,
            UsageLedger.charge_type,
            UsageLedger.currency,
        )
    )
    rows = result.all()

    return UsageSummary(
        items=[
            UsageSummaryItem(
                service_id=row.service_id,
                service_version=row.service_version,
                charge_type=row.charge_type,
                total_units=int(row.total_units or 0),
                total_amount=float(row.total_amount or 0),
                currency=row.currency,
            )
            for row in rows
        ],
        start_date=start_date,
        end_date=end_date,
    )
