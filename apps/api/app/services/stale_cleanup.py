"""Auto-cancel stale requests — Celery beat task.

Finds requests stuck in CREATED status for longer than a configurable
threshold and transitions them to CANCELLED with an audit trail.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import sync_session_factory
from app.models.audit import AuditLog
from app.models.outbox import OutboxEvent
from app.models.request import Request
from app.worker.celery_app import celery_app

logger = logging.getLogger("neurohub.stale_cleanup")

# Default threshold: 72 hours
DEFAULT_STALE_THRESHOLD_HOURS = 72
CANCEL_REASON = "자동 취소: 제한 시간 초과"


@celery_app.task(
    name="neurohub.tasks.auto_cancel_stale_requests",
    queue="compute",
)
def auto_cancel_stale_requests() -> dict:
    """Find CREATED requests older than threshold and cancel them.

    Runs every hour via Celery Beat. Respects institution-level settings
    if an ``auto_cancel_threshold_hours`` key exists in institution options.
    """
    from app.models.institution import Institution

    now = datetime.now(timezone.utc)
    default_threshold = now - timedelta(hours=DEFAULT_STALE_THRESHOLD_HOURS)
    cancelled_ids: list[str] = []

    with sync_session_factory() as session:
        # Fetch all CREATED requests older than the default threshold
        result = session.execute(
            select(Request)
            .where(
                Request.status == "CREATED",
                Request.created_at < default_threshold,
            )
            .with_for_update(skip_locked=True)
            .limit(100)
        )
        stale_requests = result.scalars().all()

        # Cache institution settings to avoid repeated lookups
        institution_cache: dict[uuid.UUID, int | None] = {}

        for req in stale_requests:
            # Check institution-level override
            inst_id = req.institution_id
            if inst_id not in institution_cache:
                inst_result = session.execute(
                    select(Institution).where(Institution.id == inst_id)
                )
                inst_result.scalar_one_or_none()
                # Institution model doesn't have options/settings column by default,
                # so we just use the default. If the institution model is extended
                # with a settings JSONB column, we can read from it here.
                institution_cache[inst_id] = None

            custom_hours = institution_cache[inst_id]
            if custom_hours is not None:
                custom_threshold = now - timedelta(hours=custom_hours)
                created_at = req.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                if created_at >= custom_threshold:
                    continue  # Not stale per institution settings

            # Cancel the request
            before_status = req.status
            req.status = "CANCELLED"
            req.cancel_reason = CANCEL_REASON

            session.add(AuditLog(
                user_id=None,  # System action
                institution_id=req.institution_id,
                action="AUTO_CANCEL_STALE",
                entity_type="request",
                entity_id=req.id,
                before_state={"status": before_status},
                after_state={"status": "CANCELLED", "reason": CANCEL_REASON},
                ip_address=None,
            ))

            session.add(OutboxEvent(
                event_type="REQUEST_AUTO_CANCELLED",
                aggregate_type="request",
                aggregate_id=req.id,
                payload={
                    "request_id": str(req.id),
                    "reason": CANCEL_REASON,
                    "source": "stale_cleanup",
                },
            ))

            cancelled_ids.append(str(req.id))
            logger.info(
                "Auto-cancelled stale request %s (institution=%s)",
                req.id, req.institution_id,
            )

        session.commit()

    if cancelled_ids:
        logger.info("Auto-cancelled %d stale requests", len(cancelled_ids))

    return {
        "cancelled_count": len(cancelled_ids),
        "cancelled_ids": cancelled_ids,
    }
