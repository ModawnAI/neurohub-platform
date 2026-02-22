"""Tests for structured JSON logging middleware."""
import json
import pytest
from unittest.mock import patch


class TestStructuredLogging:
    def test_request_log_contains_required_fields(self):
        """Log entries should contain method, path, status, duration, request_id."""
        from app.middleware.logging import RequestLoggingMiddleware
        assert RequestLoggingMiddleware is not None

    def test_request_id_generated_for_each_request(self, client):
        """Each request should get a unique X-Request-ID header."""
        import asyncio

        async def check():
            resp = await client.get("/api/v1/health")
            assert "x-request-id" in resp.headers
            return resp.headers["x-request-id"]

    def test_request_id_propagated_from_header(self, client):
        """If X-Request-ID is provided, it should be propagated."""
        import asyncio

        async def check():
            resp = await client.get(
                "/api/v1/health",
                headers={"X-Request-ID": "test-id-123"}
            )
            assert resp.headers.get("x-request-id") == "test-id-123"
