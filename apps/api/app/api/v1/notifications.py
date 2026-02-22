"""Notification endpoints for listing, reading, and marking notifications."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, update

from app.dependencies import AuthenticatedUser, DbSession
from app.models.notification import Notification
from app.schemas.pagination import PaginatedResponse

router = APIRouter(tags=["Notifications"])


class NotificationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    event_type: str
    title: str
    body: str | None = None
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    is_read: bool
    created_at: datetime


@router.get("/notifications", response_model=PaginatedResponse[NotificationRead])
async def list_notifications(
    db: DbSession,
    user: AuthenticatedUser,
    unread_only: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    base_filter = [
        Notification.user_id == user.id,
        Notification.institution_id == user.institution_id,
    ]
    if unread_only:
        base_filter.append(Notification.is_read == False)  # noqa: E712

    count_result = await db.execute(
        select(func.count(Notification.id)).where(*base_filter)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Notification)
        .where(*base_filter)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = [
        NotificationRead(
            id=n.id,
            event_type=n.event_type,
            title=n.title,
            body=n.body,
            entity_type=n.entity_type,
            entity_id=n.entity_id,
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in result.scalars().all()
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + limit) < total,
    )


@router.post("/notifications/{notification_id}/read")
async def mark_read(
    notification_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
            Notification.institution_id == user.institution_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    await db.flush()
    return {"status": "ok"}


@router.post("/notifications/read-all")
async def mark_all_read(
    db: DbSession,
    user: AuthenticatedUser,
):
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.institution_id == user.institution_id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    await db.flush()
    return {"status": "ok"}
