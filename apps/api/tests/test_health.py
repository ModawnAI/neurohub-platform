"""Tests for health endpoints.

Tests validate:
- /health returns 200 with status, version, timestamp
- /health/live always returns 200
- /health/ready checks DB and Redis connectivity
"""

import pytest


class TestHealthEndpoint:
    """Existing health endpoint."""

    async def test_health_returns_200(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data


class TestLivenessProbe:
    """Liveness probe should always return 200."""

    async def test_live_returns_200(self, client):
        resp = await client.get("/api/v1/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestReadinessProbe:
    """Readiness probe should check DB and Redis."""

    async def test_ready_returns_200_when_healthy(self, client):
        resp = await client.get("/api/v1/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert "checks" in data
        assert data["checks"]["database"] == "ok"
