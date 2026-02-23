"""Webhook notification service for B2B integrations.

Provides HMAC-signed webhook delivery with retry logic and delivery logging.
"""

import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("neurohub.webhooks")


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
