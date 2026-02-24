"""Outbox event reconciler.

Polls the outbox_events table for PENDING events and dispatches them
to the appropriate Celery queues. Also performs:
- Stale run detection (heartbeat-based)
- Usage ledger consistency checks
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select

from app.config import settings
from app.database import async_session_factory
from app.models.billing import UsageLedger
from app.models.outbox import MAX_RETRIES, OutboxEvent
from app.models.request import Request
from app.models.run import Run
from app.models.webhook import Webhook
from app.services.webhook_service import WebhookDelivery, build_webhook_payload
from app.worker.celery_app import celery_app

logger = logging.getLogger("neurohub.reconciler")

# Stale run threshold: runs RUNNING with no heartbeat (configurable via settings)
STALE_RUN_THRESHOLD_SECONDS = settings.stale_run_threshold_minutes * 60
# Max retries for stale runs before marking FAILED (configurable via settings)
STALE_RUN_MAX_RETRIES = settings.max_run_retries

# Auto-cancel threshold: requests in CREATED state for more than 7 days
STALE_CREATED_THRESHOLD_DAYS = 7


def _should_auto_cancel(status: str, created_at: datetime) -> bool:
    """Check if a request should be auto-cancelled."""
    if status != "CREATED":
        return False
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - created_at
    return age.days >= STALE_CREATED_THRESHOLD_DAYS


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


def _dispatch_run_completed(event: OutboxEvent) -> None:
    """When all runs complete and request moved to REPORTING, trigger report generation."""
    request_status = event.payload.get("request_status")
    if request_status == "REPORTING":
        celery_app.send_task(
            "neurohub.tasks.generate_report",
            args=[event.payload["request_id"]],
            queue="reporting",
        )


def _dispatch_pipeline(event: OutboxEvent) -> None:
    """Dispatch pipeline runs (same as RUN_SUBMITTED)."""
    run_ids = event.payload.get("run_ids", [])
    for run_id in run_ids:
        celery_app.send_task(
            "neurohub.tasks.execute_run",
            args=[run_id],
            queue="compute",
        )


def _dispatch_watermark_requested(event: OutboxEvent) -> None:
    celery_app.send_task(
        "neurohub.tasks.apply_watermark",
        args=[event.payload["request_id"], event.payload["evaluation_id"]],
        queue="compute",
    )


EVENT_HANDLERS: dict[str, callable] = {
    "RUN_SUBMITTED": _dispatch_run_submitted,
    "REPORT_REQUESTED": _dispatch_report_requested,
    "RUN_COMPLETED": _dispatch_run_completed,
    "PIPELINE_DISPATCHED": _dispatch_pipeline,
    "WATERMARK_REQUESTED": _dispatch_watermark_requested,
}


def _dispatch(event: OutboxEvent) -> None:
    """Route an outbox event to the correct Celery task."""
    handler = EVENT_HANDLERS.get(event.event_type)
    if handler:
        handler(event)
    else:
        logger.warning(
            "Unknown event type %s (id=%s), marking as processed", event.event_type, event.id
        )


async def _deliver_webhooks(event: OutboxEvent) -> None:
    """Deliver webhook notifications for an outbox event to matching subscriptions."""
    institution_id = None
    if event.payload:
        request_id = event.payload.get("request_id")
        if request_id:
            async with async_session_factory() as session:
                req = await session.execute(
                    select(Request).where(Request.id == uuid.UUID(request_id))
                )
                request = req.scalar_one_or_none()
                if request:
                    institution_id = request.institution_id

    if not institution_id:
        return

    async with async_session_factory() as session:
        result = await session.execute(
            select(Webhook).where(
                Webhook.institution_id == institution_id,
                Webhook.status == "ACTIVE",
            )
        )
        webhooks = result.scalars().all()

        for wh in webhooks:
            # Check if this webhook subscribes to this event type
            subscribed_events = wh.events or []
            if subscribed_events and event.event_type not in subscribed_events:
                continue

            payload = build_webhook_payload(event.event_type, event.payload or {})
            delivery = WebhookDelivery(
                webhook_url=wh.url,
                payload=payload,
                secret=wh.secret_hash,
            )
            success = delivery.deliver()
            if success:
                wh.last_delivered_at = datetime.now(timezone.utc)
                wh.failure_count = 0
            else:
                wh.failure_count = (wh.failure_count or 0) + 1
            await session.commit()


# ---------------------------------------------------------------------------
# Core outbox reconciler loop
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
                # Deliver webhooks for this event (non-blocking best-effort)
                try:
                    await _deliver_webhooks(event)
                except Exception as wh_exc:
                    logger.warning("Webhook delivery failed for event %s: %s", event.id, wh_exc)
            except Exception as exc:
                event.retry_count += 1
                event.error_detail = str(exc)[:2000]
                if event.retry_count >= MAX_RETRIES:
                    event.status = "DEAD_LETTER"
                    logger.error(
                        "Event %s dead-lettered after %d retries: %s",
                        event.id,
                        event.retry_count,
                        exc,
                    )
                else:
                    # Exponential backoff: 5s * 2^retry_count
                    backoff = timedelta(seconds=5 * (2**event.retry_count))
                    event.available_at = datetime.now(timezone.utc) + backoff
                    logger.warning(
                        "Event %s dispatch failed (retry %d/%d), next at %s: %s",
                        event.id,
                        event.retry_count,
                        MAX_RETRIES,
                        event.available_at,
                        exc,
                    )

        await session.commit()
        if dispatched:
            logger.info("Reconciler dispatched %d / %d outbox events", dispatched, len(events))
        return dispatched


# ---------------------------------------------------------------------------
# Stale run detection (PRD Section 15.3)
# ---------------------------------------------------------------------------


async def reconcile_stale_runs() -> int:
    """Detect and handle runs stuck in RUNNING state with stale heartbeats."""
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(seconds=STALE_RUN_THRESHOLD_SECONDS)
    remediated = 0

    async with async_session_factory() as session:
        result = await session.execute(
            select(Run)
            .where(
                Run.status == "RUNNING",
                Run.heartbeat_at < threshold,
            )
            .with_for_update(skip_locked=True)
            .limit(20)
        )
        stale_runs = result.scalars().all()

        for run in stale_runs:
            if run.retry_count < STALE_RUN_MAX_RETRIES:
                # Soft retry: re-enqueue via outbox
                run.retry_count += 1
                run.status = "PENDING"
                run.heartbeat_at = now
                session.add(
                    OutboxEvent(
                        event_type="RUN_SUBMITTED",
                        aggregate_type="run",
                        aggregate_id=run.request_id,
                        payload={
                            "request_id": str(run.request_id),
                            "run_ids": [str(run.id)],
                            "reason": "stale_retry",
                        },
                    )
                )
                logger.warning(
                    "Stale run %s re-enqueued (retry %d/%d)",
                    run.id,
                    run.retry_count,
                    STALE_RUN_MAX_RETRIES,
                )
            else:
                # Mark as FAILED after max retries
                run.status = "FAILED"
                run.completed_at = now
                run.error_detail = f"Stale run timed out after {run.retry_count} retries"

                # Create RELEASE ledger entry if missing
                release_exists = await session.execute(
                    select(UsageLedger.id).where(
                        UsageLedger.run_id == run.id,
                        UsageLedger.charge_type == "RELEASE",
                    )
                )
                if not release_exists.scalar_one_or_none():
                    session.add(
                        UsageLedger(
                            institution_id=run.institution_id,
                            request_id=run.request_id,
                            run_id=run.id,
                            service_id=None,
                            service_version="unknown",
                            charge_type="RELEASE",
                            units=0,
                            unit_price=0,
                            amount=0,
                            currency="USD",
                            idempotency_token=f"stale-release-{run.id}",
                        )
                    )

                logger.error("Stale run %s marked FAILED after max retries", run.id)

            remediated += 1

        await session.commit()
        if remediated:
            logger.info("Reconciled %d stale runs", remediated)
        return remediated


# ---------------------------------------------------------------------------
# Ledger consistency check (PRD Section 15.3)
# ---------------------------------------------------------------------------


async def reconcile_ledger() -> int:
    """Check for SUCCEEDED runs missing CAPTURE and FAILED runs missing RELEASE."""
    fixed = 0
    datetime.now(timezone.utc)

    async with async_session_factory() as session:
        # Find SUCCEEDED runs missing CAPTURE
        succeeded_runs = await session.execute(
            select(Run)
            .outerjoin(
                UsageLedger,
                and_(UsageLedger.run_id == Run.id, UsageLedger.charge_type == "CAPTURE"),
            )
            .where(
                Run.status == "SUCCEEDED",
                Run.completed_at.isnot(None),
                UsageLedger.id.is_(None),
            )
            .limit(50)
        )
        for run in succeeded_runs.scalars().all():
            session.add(
                UsageLedger(
                    institution_id=run.institution_id,
                    request_id=run.request_id,
                    run_id=run.id,
                    service_id=None,
                    service_version="unknown",
                    charge_type="CAPTURE",
                    units=1,
                    unit_price=0,
                    amount=run.cost_amount or 0,
                    currency="USD",
                    idempotency_token=f"reconcile-capture-{run.id}",
                )
            )
            fixed += 1
            logger.warning("Created missing CAPTURE ledger entry for run %s", run.id)

        # Find FAILED runs missing RELEASE
        failed_runs = await session.execute(
            select(Run)
            .outerjoin(
                UsageLedger,
                and_(UsageLedger.run_id == Run.id, UsageLedger.charge_type == "RELEASE"),
            )
            .where(
                Run.status == "FAILED",
                Run.completed_at.isnot(None),
                UsageLedger.id.is_(None),
            )
            .limit(50)
        )
        for run in failed_runs.scalars().all():
            session.add(
                UsageLedger(
                    institution_id=run.institution_id,
                    request_id=run.request_id,
                    run_id=run.id,
                    service_id=None,
                    service_version="unknown",
                    charge_type="RELEASE",
                    units=0,
                    unit_price=0,
                    amount=0,
                    currency="USD",
                    idempotency_token=f"reconcile-release-{run.id}",
                )
            )
            fixed += 1
            logger.warning("Created missing RELEASE ledger entry for run %s", run.id)

        await session.commit()
        if fixed:
            logger.info("Ledger reconciliation fixed %d entries", fixed)
        return fixed


# ---------------------------------------------------------------------------
# Auto-cancel stale CREATED requests (P4-25)
# ---------------------------------------------------------------------------


async def auto_cancel_stale_requests() -> int:
    """Find CREATED requests older than STALE_CREATED_THRESHOLD_DAYS and cancel them."""
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(days=STALE_CREATED_THRESHOLD_DAYS)
    cancelled = 0

    async with async_session_factory() as session:
        result = await session.execute(
            select(Request)
            .where(
                Request.status == "CREATED",
                Request.created_at < threshold,
            )
            .with_for_update(skip_locked=True)
            .limit(50)
        )
        stale_requests = result.scalars().all()

        for req in stale_requests:
            req.status = "CANCELLED"
            req.cancel_reason = (
                f"Auto-cancelled: request remained in CREATED state for over "
                f"{STALE_CREATED_THRESHOLD_DAYS} days without progressing."
            )
            session.add(
                OutboxEvent(
                    event_type="REQUEST_AUTO_CANCELLED",
                    aggregate_type="request",
                    aggregate_id=req.id,
                    payload={
                        "request_id": str(req.id),
                        "reason": "stale_created",
                        "age_days": (
                            now
                            - (
                                req.created_at.replace(tzinfo=timezone.utc)
                                if req.created_at.tzinfo is None
                                else req.created_at
                            )
                        ).days,
                    },
                )
            )
            cancelled += 1
            logger.info(
                "Auto-cancelled stale request %s (CREATED for >%d days)",
                req.id,
                STALE_CREATED_THRESHOLD_DAYS,
            )

        await session.commit()
        if cancelled:
            logger.info("Auto-cancelled %d stale CREATED requests", cancelled)
        return cancelled


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main():
    logger.info(
        "Reconciler starting — outbox every 5s, stale runs every 30s, ledger every 60s, auto-cancel every 10min"
    )
    outbox_counter = 0
    while True:
        try:
            await run_once()
            outbox_counter += 1

            # Run stale detection every ~30s (6 cycles)
            if outbox_counter % 6 == 0:
                await reconcile_stale_runs()

            # Run ledger consistency every ~60s (12 cycles)
            if outbox_counter % 12 == 0:
                await reconcile_ledger()

            # Run auto-cancel every ~10min (120 cycles)
            if outbox_counter % 120 == 0:
                await auto_cancel_stale_requests()

        except Exception:
            logger.exception("Reconciler loop failed")
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
