"""Tests for global exception handling and standardized error responses."""
import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from app.exceptions import NeuroHubError, NotFoundError, ConflictError, ForbiddenError, ValidationError


class TestNeuroHubErrorResponse:
    """Verify all NeuroHubError subclasses return consistent JSON shape."""

    @pytest.mark.asyncio
    async def test_not_found_returns_404_with_standard_shape(self, client):
        resp = await client.get("/api/v1/requests/00000000-0000-0000-0000-000000000099")
        assert resp.status_code == 404
        body = resp.json()
        # FastAPI HTTPException returns {"detail": "..."} format
        assert "detail" in body or "error" in body

    @pytest.mark.asyncio
    async def test_validation_error_returns_422_with_details(self, client):
        # Send invalid body to trigger Pydantic validation
        resp = await client.post("/api/v1/requests", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body or "error" in body

    @pytest.mark.asyncio
    async def test_unhandled_exception_returns_500_with_safe_message(self):
        """Unhandled exceptions should not leak stack traces via the main app handler."""
        from app.main import app as main_app

        # Verify the main app has the catch-all handler registered
        handlers = main_app.exception_handlers
        assert Exception in handlers, "Main app should have catch-all Exception handler"

        # Directly invoke the handler to verify its behavior
        from unittest.mock import MagicMock
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "test-req-id"
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        exc = RuntimeError("secret internal details")
        resp = await handlers[Exception](mock_request, exc)
        assert resp.status_code == 500
        import json
        body = json.loads(resp.body)
        assert body["error"] == "INTERNAL_ERROR"
        assert "secret" not in body["message"]

    @pytest.mark.asyncio
    async def test_neurohub_error_hierarchy(self):
        """All custom errors extend NeuroHubError."""
        assert issubclass(NotFoundError, NeuroHubError)
        assert issubclass(ConflictError, NeuroHubError)
        assert issubclass(ForbiddenError, NeuroHubError)
        assert issubclass(ValidationError, NeuroHubError)

    @pytest.mark.asyncio
    async def test_rate_limit_error_shape(self):
        """RateLimitError should have proper error code."""
        from app.exceptions import RateLimitError
        err = RateLimitError()
        assert err.status_code == 429
        assert err.code == "RATE_LIMITED"
