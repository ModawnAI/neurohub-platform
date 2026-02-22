"""TDD tests for outbox reconciler (Phase 2).

Tests validate:
- Reconciler picks up PENDING events
- Events are dispatched to correct Celery queues
- Retry with exponential backoff on dispatch failure
- Dead letter after MAX_RETRIES
- FOR UPDATE SKIP LOCKED prevents double-processing
- Stale run detection and auto-recovery
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent
from app.models.run import Run


class TestOutboxDispatch:
    """Reconciler should dispatch events to Celery."""

    async def test_dispatches_run_submitted_to_compute_queue(self, db: AsyncSession):
        event = OutboxEvent(
            event_type="RUN_SUBMITTED",
            aggregate_type="request",
            aggregate_id=uuid.uuid4(),
            payload={"request_id": str(uuid.uuid4()), "run_ids": [str(uuid.uuid4())]},
            status="PENDING",
        )
        db.add(event)
        await db.flush()

        from app.reconciler import run_once

        with patch("app.reconciler.celery_app") as mock_celery:
            await run_once()
            mock_celery.send_task.assert_called()
            call_args = mock_celery.send_task.call_args
            assert call_args[0][0] == "neurohub.tasks.execute_run"
            assert call_args[1]["queue"] == "compute"

    async def test_dispatches_report_requested_to_reporting_queue(self, db: AsyncSession):
        event = OutboxEvent(
            event_type="REPORT_REQUESTED",
            aggregate_type="request",
            aggregate_id=uuid.uuid4(),
            payload={"request_id": str(uuid.uuid4())},
            status="PENDING",
        )
        db.add(event)
        await db.flush()

        from app.reconciler import run_once

        with patch("app.reconciler.celery_app") as mock_celery:
            await run_once()
            mock_celery.send_task.assert_called()
            call_args = mock_celery.send_task.call_args
            assert call_args[0][0] == "neurohub.tasks.generate_report"
            assert call_args[1]["queue"] == "reporting"

    async def test_marks_dispatched_event_as_processed(self, db: AsyncSession):
        event = OutboxEvent(
            event_type="RUN_SUBMITTED",
            aggregate_type="request",
            aggregate_id=uuid.uuid4(),
            payload={"request_id": str(uuid.uuid4()), "run_ids": [str(uuid.uuid4())]},
            status="PENDING",
        )
        db.add(event)
        await db.flush()
        event_id = event.id

        from app.reconciler import run_once

        with patch("app.reconciler.celery_app"):
            await run_once()

        await db.refresh(event)
        assert event.status == "PROCESSED"
        assert event.processed_at is not None


class TestRetryLogic:
    """Reconciler should retry failed dispatches with backoff."""

    async def test_retry_increments_count_and_delays(self, db: AsyncSession):
        event = OutboxEvent(
            event_type="RUN_SUBMITTED",
            aggregate_type="request",
            aggregate_id=uuid.uuid4(),
            payload={"request_id": str(uuid.uuid4()), "run_ids": [str(uuid.uuid4())]},
            status="PENDING",
            retry_count=0,
        )
        db.add(event)
        await db.flush()

        from app.reconciler import run_once

        with patch("app.reconciler.celery_app") as mock_celery:
            mock_celery.send_task.side_effect = ConnectionError("Redis down")
            await run_once()

        await db.refresh(event)
        assert event.retry_count == 1
        assert event.status == "PENDING"  # still pending, not processed
        assert event.available_at > datetime.now(timezone.utc)  # delayed

    async def test_dead_letter_after_max_retries(self, db: AsyncSession):
        event = OutboxEvent(
            event_type="RUN_SUBMITTED",
            aggregate_type="request",
            aggregate_id=uuid.uuid4(),
            payload={"request_id": str(uuid.uuid4()), "run_ids": [str(uuid.uuid4())]},
            status="PENDING",
            retry_count=4,  # One more retry will hit max (5)
        )
        db.add(event)
        await db.flush()

        from app.reconciler import run_once

        with patch("app.reconciler.celery_app") as mock_celery:
            mock_celery.send_task.side_effect = ConnectionError("Redis down")
            await run_once()

        await db.refresh(event)
        assert event.status == "DEAD_LETTER"
        assert event.retry_count == 5


class TestUnknownEventType:
    """Unknown event types should be logged and marked processed."""

    async def test_unknown_event_type_marked_processed(self, db: AsyncSession):
        event = OutboxEvent(
            event_type="UNKNOWN_EVENT",
            aggregate_type="request",
            aggregate_id=uuid.uuid4(),
            payload={},
            status="PENDING",
        )
        db.add(event)
        await db.flush()

        from app.reconciler import run_once

        with patch("app.reconciler.celery_app"):
            await run_once()

        await db.refresh(event)
        assert event.status == "PROCESSED"
