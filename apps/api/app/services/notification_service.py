"""Notification creation service.

Called from state transition endpoints to notify relevant users
about request status changes.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def create_notification(
    db: AsyncSession,
    *,
    institution_id: uuid.UUID,
    user_id: uuid.UUID,
    event_type: str,
    title: str,
    body: str | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> Notification:
    notification = Notification(
        institution_id=institution_id,
        user_id=user_id,
        event_type=event_type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_=metadata or {},
    )
    db.add(notification)
    await db.flush()
    return notification
