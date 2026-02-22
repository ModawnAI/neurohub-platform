"""Webhook management endpoints."""
import hashlib
import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.dependencies import AuthenticatedUser, DbSession, require_roles
from app.models.webhook import Webhook

router = APIRouter(prefix="/organizations/{org_id}/webhooks", tags=["Webhooks"])


class WebhookCreate(BaseModel):
    url: str = Field(..., min_length=10, max_length=500)
    events: list[str] = Field(default=["REQUEST_STATUS_CHANGED"])
    secret: str = Field(..., min_length=8, max_length=200)


class WebhookRead(BaseModel):
    id: uuid.UUID
    url: str
    events: list[str]
    status: str
    created_at: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_webhook(
    org_id: uuid.UUID,
    body: WebhookCreate,
    db: DbSession,
    user: AuthenticatedUser,
):
    if user.institution_id != org_id and not user.has_any_role("SYSTEM_ADMIN"):
        raise HTTPException(status_code=403, detail="Not authorized")

    webhook = Webhook(
        institution_id=org_id,
        url=body.url,
        secret_hash=hashlib.sha256(body.secret.encode()).hexdigest(),
        events=body.events,
        status="ACTIVE",
    )
    db.add(webhook)
    await db.flush()
    return {"id": str(webhook.id), "url": webhook.url, "events": webhook.events, "status": webhook.status}


@router.get("")
async def list_webhooks(
    org_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    if user.institution_id != org_id and not user.has_any_role("SYSTEM_ADMIN"):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(Webhook).where(Webhook.institution_id == org_id, Webhook.status == "ACTIVE")
    )
    webhooks = result.scalars().all()
    return {
        "items": [
            {"id": str(w.id), "url": w.url, "events": w.events, "status": w.status}
            for w in webhooks
        ]
    }


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    org_id: uuid.UUID,
    webhook_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    if user.institution_id != org_id and not user.has_any_role("SYSTEM_ADMIN"):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.institution_id == org_id)
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    webhook.status = "DELETED"
    await db.flush()
