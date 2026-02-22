"""Tests for auto-cancellation of stale CREATED requests."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch


class TestAutoCancel:
    def test_stale_threshold_configurable(self):
        """Stale threshold should be configurable."""
        from app.reconciler import STALE_CREATED_THRESHOLD_DAYS
        assert STALE_CREATED_THRESHOLD_DAYS > 0

    def test_auto_cancel_skips_non_created(self):
        """Only CREATED requests should be auto-cancelled."""
        # Requests in RECEIVING, STAGING, etc. should not be cancelled
        from app.reconciler import _should_auto_cancel
        assert _should_auto_cancel("CREATED", datetime.now(timezone.utc) - timedelta(days=8)) is True
        assert _should_auto_cancel("RECEIVING", datetime.now(timezone.utc) - timedelta(days=8)) is False
        assert _should_auto_cancel("COMPUTING", datetime.now(timezone.utc) - timedelta(days=8)) is False

    def test_auto_cancel_respects_threshold(self):
        """Requests younger than threshold should not be cancelled."""
        from app.reconciler import _should_auto_cancel
        # Recent request - should not cancel
        assert _should_auto_cancel("CREATED", datetime.now(timezone.utc) - timedelta(days=1)) is False
        # Old request - should cancel
        assert _should_auto_cancel("CREATED", datetime.now(timezone.utc) - timedelta(days=8)) is True
