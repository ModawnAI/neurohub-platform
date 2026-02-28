"""Tests for Redis-backed rate limiting middleware."""
import pytest
from unittest.mock import patch

from app.middleware.rate_limit import (
    _CATEGORY_LIMITS,
    _InMemoryLimiter,
    _get_rate_limiter,
)

_LIMIT_UNAUTH = _CATEGORY_LIMITS["read"]["unauth"]  # 60
_LIMIT_AUTH = _CATEGORY_LIMITS["read"]["auth"]  # 300


class TestRateLimitMiddleware:
    @pytest.mark.asyncio
    async def test_health_check_bypasses_rate_limit(self, client):
        """Health endpoints should never be rate-limited."""
        for _ in range(100):
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200

    def test_in_memory_limiter_returns_429_after_limit(self):
        """Verify in-memory limiter blocks after exceeding limit."""
        limiter = _InMemoryLimiter()
        key = "test_ip_exhaustion"
        for i in range(_LIMIT_UNAUTH):
            allowed, _ = limiter.check_and_increment(key, _LIMIT_UNAUTH)
            assert allowed, f"Request {i} should be allowed"

        # Next request should be blocked
        allowed, count = limiter.check_and_increment(key, _LIMIT_UNAUTH)
        assert not allowed, "Should be rate limited after exceeding limit"
        assert count >= _LIMIT_UNAUTH

    def test_authenticated_gets_higher_limit(self):
        """Authenticated users get 300/min vs 60/min."""
        assert _LIMIT_AUTH > _LIMIT_UNAUTH
        assert _LIMIT_AUTH == 300
        assert _LIMIT_UNAUTH == 60

    def test_rate_limiter_factory_returns_limiter(self):
        """_get_rate_limiter should return a non-None limiter."""
        limiter = _get_rate_limiter()
        assert limiter is not None

    def test_in_memory_limiter_allows_after_window(self):
        """After the time window, requests should be allowed again."""
        import time
        from app.middleware.rate_limit import _buckets

        limiter = _InMemoryLimiter()
        key = "test_window_reset"
        # Fill up the bucket with timestamps that are already expired
        _buckets[key] = [time.time() - 120] * _LIMIT_UNAUTH
        # Should be allowed since old timestamps are cleaned up
        allowed, _ = limiter.check_and_increment(key, _LIMIT_UNAUTH)
        assert allowed, "Should be allowed after window expiry"
