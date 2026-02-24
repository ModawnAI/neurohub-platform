"""Tests for Prometheus metrics endpoint."""

import pytest


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_200(self, client):
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_metrics_contains_request_count(self, client):
        await client.get("/api/v1/health")
        resp = await client.get("/metrics")
        assert "http_requests_total" in resp.text

    @pytest.mark.asyncio
    async def test_metrics_contains_histogram(self, client):
        await client.get("/api/v1/health")
        resp = await client.get("/metrics")
        assert "http_request_duration_seconds_bucket" in resp.text
        assert "http_request_duration_seconds_sum" in resp.text
        assert "http_request_duration_seconds_count" in resp.text

    @pytest.mark.asyncio
    async def test_metrics_contains_active_connections(self, client):
        resp = await client.get("/metrics")
        assert "http_active_connections" in resp.text

    @pytest.mark.asyncio
    async def test_metrics_contains_error_counter_after_4xx(self, client):
        await client.get("/api/v1/requests/00000000-0000-0000-0000-000000000000")
        resp = await client.get("/metrics")
        assert "http_errors_total" in resp.text
