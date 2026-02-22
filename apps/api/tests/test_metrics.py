"""Tests for Prometheus metrics endpoint."""
import pytest


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_200(self, client):
        """The /metrics endpoint should return Prometheus-format metrics."""
        resp = await client.get("/metrics")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_contains_request_count(self, client):
        """Metrics should include HTTP request counts."""
        # Make a request first
        await client.get("/api/v1/health")
        resp = await client.get("/metrics")
        text = resp.text
        assert "http_request" in text.lower() or "request" in text.lower()
