"""Webhook management endpoints with CRUD and delivery log access."""

import hashlib
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.dependencies import AuthenticatedUser, DbSession
from app.models.webhook import Webhook, WebhookDeliveryLog

router = APIRouter(prefix="/organizations/{org_id}/webhooks", tags=["Webhooks"])


class WebhookCreate(BaseModel):
    url: str = Field(..., min_length=10, max_length=500)
    events: list[str] = Field(default=["REQUEST_STATUS_CHANGED"])
    secret: str = Field(..., min_length=8, max_length=200)
    description: str | None = Field(default=None, max_length=500)


class WebhookUpdate(BaseModel):
    url: str | None = Field(default=None, min_length=10, max_length=500)
    events: list[str] | None = None
    secret: str | None = Field(default=None, min_length=8, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, pattern="^(ACTIVE|PAUSED)$")


class WebhookRead(BaseModel):
    id: uuid.UUID
    url: str
    events: list[str]
    status: str
    description: str | None = None
    failure_count: int = 0
    last_delivered_at: str | None = None
    created_at: str | None = None


class WebhookDeliveryLogRead(BaseModel):
    id: uuid.UUID
    event_type: str
    success: bool
    status_code: int | None = None
    attempt: int = 1
    error_detail: str | None = None
    delivered_at: str | None = None


def _check_org_access(user: AuthenticatedUser, org_id: uuid.UUID) -> None:
    if user.institution_id != org_id and not user.has_any_role("SYSTEM_ADMIN"):
        raise HTTPException(status_code=403, detail="Not authorized")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_webhook(
    org_id: uuid.UUID,
    body: WebhookCreate,
    db: DbSession,
    user: AuthenticatedUser,
):
    _check_org_access(user, org_id)

    webhook = Webhook(
        institution_id=org_id,
        url=body.url,
        secret_hash=hashlib.sha256(body.secret.encode()).hexdigest(),
        events=body.events,
        status="ACTIVE",
        description=body.description,
    )
    db.add(webhook)
    await db.flush()
    return {
        "id": str(webhook.id),
        "url": webhook.url,
        "events": webhook.events,
        "status": webhook.status,
        "description": webhook.description,
    }


@router.get("")
async def list_webhooks(
    org_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
    include_paused: bool = Query(default=False),
):
    _check_org_access(user, org_id)

    statuses = ["ACTIVE"]
    if include_paused:
        statuses.append("PAUSED")

    result = await db.execute(
        select(Webhook).where(
            Webhook.institution_id == org_id,
            Webhook.status.in_(statuses),
        )
    )
    webhooks = result.scalars().all()
    return {
        "items": [
            {
                "id": str(w.id),
                "url": w.url,
                "events": w.events,
                "status": w.status,
                "description": w.description,
                "failure_count": w.failure_count,
                "last_delivered_at": w.last_delivered_at.isoformat()
                if w.last_delivered_at
                else None,
            }
            for w in webhooks
        ]
    }


@router.patch("/{webhook_id}")
async def update_webhook(
    org_id: uuid.UUID,
    webhook_id: uuid.UUID,
    body: WebhookUpdate,
    db: DbSession,
    user: AuthenticatedUser,
):
    _check_org_access(user, org_id)

    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.institution_id == org_id)
    )
    webhook = result.scalar_one_or_none()
    if not webhook or webhook.status == "DELETED":
        raise HTTPException(status_code=404, detail="Webhook not found")

    if body.url is not None:
        webhook.url = body.url
    if body.events is not None:
        webhook.events = body.events
    if body.secret is not None:
        webhook.secret_hash = hashlib.sha256(body.secret.encode()).hexdigest()
    if body.description is not None:
        webhook.description = body.description
    if body.status is not None:
        webhook.status = body.status

    await db.flush()
    return {
        "id": str(webhook.id),
        "url": webhook.url,
        "events": webhook.events,
        "status": webhook.status,
        "description": webhook.description,
    }


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    org_id: uuid.UUID,
    webhook_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    _check_org_access(user, org_id)

    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.institution_id == org_id)
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    webhook.status = "DELETED"
    await db.flush()


@router.get("/{webhook_id}/deliveries")
async def list_delivery_logs(
    org_id: uuid.UUID,
    webhook_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
    limit: int = Query(default=50, ge=1, le=200),
):
    """List recent delivery logs for a webhook."""
    _check_org_access(user, org_id)

    # Verify webhook belongs to org
    wh_result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.institution_id == org_id)
    )
    if not wh_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Webhook not found")

    result = await db.execute(
        select(WebhookDeliveryLog)
        .where(WebhookDeliveryLog.webhook_id == webhook_id)
        .order_by(WebhookDeliveryLog.delivered_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return {
        "items": [
            {
                "id": str(log.id),
                "event_type": log.event_type,
                "success": log.success,
                "status_code": log.status_code,
                "attempt": log.attempt,
                "error_detail": log.error_detail,
                "delivered_at": log.delivered_at.isoformat() if log.delivered_at else None,
            }
            for log in logs
        ]
    }
