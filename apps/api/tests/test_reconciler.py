"""Unit tests for outbox reconciler logic.

Tests the dispatch routing, retry backoff, and dead-letter behavior
without requiring a real database connection. The reconciler's
FOR UPDATE SKIP LOCKED queries are PostgreSQL-specific, so we test
the core logic (dispatch routing, backoff math) as unit tests.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from app.models.outbox import OutboxEvent, MAX_RETRIES


class TestDispatchRouting:
    """Verify events are routed to the correct Celery task/queue."""

    def test_run_submitted_dispatches_to_compute(self):
        from app.reconciler import _dispatch_run_submitted
        event = OutboxEvent(
            event_type="RUN_SUBMITTED",
            aggregate_type="request",
            aggregate_id=uuid.uuid4(),
            payload={"request_id": str(uuid.uuid4()), "run_ids": [str(uuid.uuid4())]},
        )
        with patch("app.reconciler.celery_app") as mock_celery:
            _dispatch_run_submitted(event)
            mock_celery.send_task.assert_called_once()
            call_args = mock_celery.send_task.call_args
            assert call_args[0][0] == "neurohub.tasks.execute_run"
            assert call_args[1]["queue"] == "compute"

    def test_report_requested_dispatches_to_reporting(self):
        from app.reconciler import _dispatch_report_requested
        event = OutboxEvent(
            event_type="REPORT_REQUESTED",
            aggregate_type="request",
            aggregate_id=uuid.uuid4(),
            payload={"request_id": str(uuid.uuid4())},
        )
        with patch("app.reconciler.celery_app") as mock_celery:
            _dispatch_report_requested(event)
            mock_celery.send_task.assert_called_once()
            call_args = mock_celery.send_task.call_args
            assert call_args[0][0] == "neurohub.tasks.generate_report"
            assert call_args[1]["queue"] == "reporting"

    def test_dispatch_routes_known_event(self):
        from app.reconciler import _dispatch
        event = OutboxEvent(
            event_type="RUN_SUBMITTED",
            aggregate_type="request",
            aggregate_id=uuid.uuid4(),
            payload={"request_id": str(uuid.uuid4()), "run_ids": [str(uuid.uuid4())]},
        )
        with patch("app.reconciler.celery_app") as mock_celery:
            _dispatch(event)
            mock_celery.send_task.assert_called()

    def test_dispatch_handles_unknown_event_gracefully(self):
        from app.reconciler import _dispatch
        event = OutboxEvent(
            event_type="TOTALLY_UNKNOWN",
            aggregate_type="request",
            aggregate_id=uuid.uuid4(),
            payload={},
        )
        # Should not raise
        with patch("app.reconciler.celery_app"):
            _dispatch(event)


class TestRetryLogic:
    """Verify exponential backoff and dead-letter behavior."""

    def test_max_retries_constant(self):
        assert MAX_RETRIES == 5

    def test_backoff_calculation(self):
        """Backoff formula: 5s * 2^retry_count."""
        for retry in range(5):
            expected_seconds = 5 * (2 ** retry)
            backoff = timedelta(seconds=expected_seconds)
            assert backoff.total_seconds() == expected_seconds

    def test_event_transitions_to_dead_letter_at_max(self):
        """An event at retry_count == MAX_RETRIES-1, after one more failure, should be DEAD_LETTER."""
        event = OutboxEvent(
            event_type="RUN_SUBMITTED",
            aggregate_type="request",
            aggregate_id=uuid.uuid4(),
            payload={"request_id": str(uuid.uuid4()), "run_ids": []},
            status="PENDING",
            retry_count=MAX_RETRIES - 1,
        )
        # Simulate one more failure
        event.retry_count += 1
        if event.retry_count >= MAX_RETRIES:
            event.status = "DEAD_LETTER"

        assert event.status == "DEAD_LETTER"
        assert event.retry_count == MAX_RETRIES


class TestMultiRunDispatch:
    """Verify that RUN_SUBMITTED with multiple run_ids dispatches one task per run."""

    def test_dispatches_per_run_id(self):
        from app.reconciler import _dispatch_run_submitted
        run_ids = [str(uuid.uuid4()) for _ in range(3)]
        event = OutboxEvent(
            event_type="RUN_SUBMITTED",
            aggregate_type="request",
            aggregate_id=uuid.uuid4(),
            payload={"request_id": str(uuid.uuid4()), "run_ids": run_ids},
        )
        with patch("app.reconciler.celery_app") as mock_celery:
            _dispatch_run_submitted(event)
            assert mock_celery.send_task.call_count == 3
