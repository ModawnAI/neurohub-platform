"""Outbox event reconciler.

Polls the outbox_events table for PENDING events and dispatches them
to the appropriate Celery queues. Implements retry with exponential
backoff and dead-letter handling.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.database import async_session_factory
from app.models.outbox import MAX_RETRIES, OutboxEvent
from app.worker.celery_app import celery_app

logger = logging.getLogger("neurohub.reconciler")


# ---------------------------------------------------------------------------
# Event dispatch routing
# ---------------------------------------------------------------------------

def _dispatch_run_submitted(event: OutboxEvent) -> None:
    run_ids = event.payload.get("run_ids", [])
    for run_id in run_ids:
        celery_app.send_task(
            "neurohub.tasks.execute_run",
            args=[run_id],
            queue="compute",
        )


def _dispatch_report_requested(event: OutboxEvent) -> None:
    celery_app.send_task(
        "neurohub.tasks.generate_report",
        args=[event.payload["request_id"]],
        queue="reporting",
    )


EVENT_HANDLERS: dict[str, callable] = {
    "RUN_SUBMITTED": _dispatch_run_submitted,
    "REPORT_REQUESTED": _dispatch_report_requested,
}


def _dispatch(event: OutboxEvent) -> None:
    """Route an outbox event to the correct Celery task."""
    handler = EVENT_HANDLERS.get(event.event_type)
    if handler:
        handler(event)
    else:
        logger.warning("Unknown event type %s (id=%s), marking as processed", event.event_type, event.id)


# ---------------------------------------------------------------------------
# Core reconciler loop
# ---------------------------------------------------------------------------

async def run_once() -> int:
    """Fetch and dispatch PENDING outbox events. Returns count dispatched."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(OutboxEvent)
            .where(
                OutboxEvent.status == "PENDING",
                OutboxEvent.available_at <= func.now(),
            )
            .order_by(OutboxEvent.available_at.asc())
            .limit(50)
            .with_for_update(skip_locked=True)
        )
        events = result.scalars().all()
        dispatched = 0

        for event in events:
            try:
                _dispatch(event)
                event.status = "PROCESSED"
                event.processed_at = datetime.now(timezone.utc)
                dispatched += 1
            except Exception as exc:
                event.retry_count += 1
                event.error_detail = str(exc)[:2000]
                if event.retry_count >= MAX_RETRIES:
                    event.status = "DEAD_LETTER"
                    logger.error(
                        "Event %s dead-lettered after %d retries: %s",
                        event.id, event.retry_count, exc,
                    )
                else:
                    # Exponential backoff: 5s * 2^retry_count
                    backoff = timedelta(seconds=5 * (2 ** event.retry_count))
                    event.available_at = datetime.now(timezone.utc) + backoff
                    logger.warning(
                        "Event %s dispatch failed (retry %d/%d), next at %s: %s",
                        event.id, event.retry_count, MAX_RETRIES, event.available_at, exc,
                    )

        await session.commit()
        if dispatched:
            logger.info("Reconciler dispatched %d / %d outbox events", dispatched, len(events))
        return dispatched


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    logger.info("Reconciler starting — polling every 5s")
    while True:
        try:
            await run_once()
        except Exception:
            logger.exception("Reconciler loop failed")
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
