"""Webhook notification service for B2B integrations.

Provides HMAC-signed webhook delivery with retry logic and delivery logging.
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("neurohub.webhooks")


class WebhookDelivery:
    """Synchronous webhook delivery with HMAC signing."""

    def __init__(self, webhook_url: str, payload: dict, secret: str | None = None):
        self.webhook_url = webhook_url
        self.payload = payload
        self.secret = secret

    def deliver(self) -> bool:
        """Deliver the webhook payload. Returns True on success."""
        try:
            payload_str = json.dumps(self.payload, default=str)
            headers = {"Content-Type": "application/json"}
            if self.secret:
                headers["X-Webhook-Signature"] = generate_webhook_signature(
                    payload_str, self.secret
                )
            with httpx.Client(timeout=10) as client:
                resp = client.post(self.webhook_url, content=payload_str, headers=headers)
            if resp.status_code < 400:
                return True
            logger.warning("Webhook delivery failed: %s %s", resp.status_code, resp.text[:200])
            return False
        except Exception as exc:
            logger.warning("Webhook delivery error: %s", exc)
            return False


def build_webhook_payload(event_type: str, data: dict) -> dict:
    return {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


def generate_webhook_signature(payload_str: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def verify_webhook_signature(payload_str: str, secret: str, signature: str) -> bool:
    """Verify HMAC signature from webhook delivery."""
    expected = generate_webhook_signature(payload_str, secret)
    return hmac.compare_digest(expected, signature)


def dispatch_webhook_event(
    event_type: str,
    data: dict,
    institution_id: str,
) -> None:
    """Queue webhook delivery for all matching webhooks (via Celery).

    Called from within a sync session context (e.g., Celery tasks or reconciler).
    """
    from sqlalchemy import select

    from app.database import sync_session_factory
    from app.models.webhook import Webhook

    with sync_session_factory() as session:
        result = session.execute(
            select(Webhook).where(
                Webhook.institution_id == uuid.UUID(institution_id),
                Webhook.status == "ACTIVE",
            )
        )
        webhooks = result.scalars().all()

        for wh in webhooks:
            events = wh.events or []
            if event_type in events or "*" in events:
                from app.worker.celery_app import celery_app

                celery_app.send_task(
                    "neurohub.tasks.deliver_webhook",
                    args=[str(wh.id), event_type, data],
                    queue="reporting",
                )


async def dispatch_webhook_event_async(
    db,
    event_type: str,
    data: dict,
    institution_id: uuid.UUID,
) -> None:
    """Async version: queue webhook delivery for matching webhooks."""
    from sqlalchemy import select

    from app.models.webhook import Webhook

    result = await db.execute(
        select(Webhook).where(
            Webhook.institution_id == institution_id,
            Webhook.status == "ACTIVE",
        )
    )
    webhooks = result.scalars().all()

    for wh in webhooks:
        events = wh.events or []
        if event_type in events or "*" in events:
            from app.worker.celery_app import celery_app

            celery_app.send_task(
                "neurohub.tasks.deliver_webhook",
                args=[str(wh.id), event_type, data],
                queue="reporting",
            )
