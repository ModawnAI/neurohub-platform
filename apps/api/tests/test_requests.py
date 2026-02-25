"""Integration tests for request lifecycle.

TDD: These tests define the expected behavior for the full request lifecycle.
Tests should be written first, then implementation made to pass them.

Tests validate:
- Create request returns 201 with correct fields
- Idempotency: same key + same payload returns cached response
- Idempotency: same key + different payload returns 409
- List requests returns paginated response
- Get request by ID
- State transitions: CREATED → RECEIVING → STAGING → confirm → submit
- Cancel request
- Cross-tenant isolation
"""

import uuid

import pytest

from tests.conftest import (
    DEFAULT_INSTITUTION_ID,
    DEFAULT_PIPELINE_ID,
    DEFAULT_SERVICE_ID,
    create_test_request,
)


class TestCreateRequest:
    """POST /api/v1/requests."""

    async def test_create_returns_201(self, client):
        resp = await client.post(
            "/api/v1/requests",
            json={
                "service_id": str(DEFAULT_SERVICE_ID),
                "pipeline_id": str(DEFAULT_PIPELINE_ID),
                "cases": [{"patient_ref": "PAT-001"}],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "CREATED"
        assert data["institution_id"] == str(DEFAULT_INSTITUTION_ID)
        assert data["case_count"] == 1

    async def test_create_with_multiple_cases(self, client):
        resp = await client.post(
            "/api/v1/requests",
            json={
                "service_id": str(DEFAULT_SERVICE_ID),
                "pipeline_id": str(DEFAULT_PIPELINE_ID),
                "cases": [
                    {"patient_ref": "PAT-001"},
                    {"patient_ref": "PAT-002"},
                    {"patient_ref": "PAT-003"},
                ],
            },
        )
        assert resp.status_code == 201
        assert resp.json()["case_count"] == 3

    async def test_create_without_cases_returns_422(self, client):
        resp = await client.post(
            "/api/v1/requests",
            json={
                "service_id": str(DEFAULT_SERVICE_ID),
                "pipeline_id": str(DEFAULT_PIPELINE_ID),
                "cases": [],
            },
        )
        assert resp.status_code == 422


class TestIdempotency:
    """Idempotency key behavior."""

    async def test_same_key_same_payload_returns_cached(self, client):
        key = f"test-idem-{uuid.uuid4()}"
        payload = {
            "service_id": str(DEFAULT_SERVICE_ID),
            "pipeline_id": str(DEFAULT_PIPELINE_ID),
            "cases": [{"patient_ref": "PAT-IDEM"}],
            "idempotency_key": key,
        }
        resp1 = await client.post("/api/v1/requests", json=payload)
        assert resp1.status_code == 201
        resp2 = await client.post("/api/v1/requests", json=payload)
        assert resp2.status_code == 200
        assert resp1.json()["id"] == resp2.json()["id"]

    async def test_same_key_different_payload_returns_409(self, client):
        key = f"test-conflict-{uuid.uuid4()}"
        payload1 = {
            "service_id": str(DEFAULT_SERVICE_ID),
            "pipeline_id": str(DEFAULT_PIPELINE_ID),
            "cases": [{"patient_ref": "PAT-A"}],
            "idempotency_key": key,
        }
        payload2 = {
            "service_id": str(DEFAULT_SERVICE_ID),
            "pipeline_id": str(DEFAULT_PIPELINE_ID),
            "cases": [{"patient_ref": "PAT-B"}],
            "idempotency_key": key,
        }
        resp1 = await client.post("/api/v1/requests", json=payload1)
        assert resp1.status_code == 201
        resp2 = await client.post("/api/v1/requests", json=payload2)
        assert resp2.status_code == 409


class TestListRequests:
    """GET /api/v1/requests with pagination."""

    async def test_list_returns_paginated_response(self, client):
        # Create a request first
        await create_test_request(client)
        resp = await client.get("/api/v1/requests", params={"offset": 0, "limit": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert "has_more" in data

    async def test_list_with_status_filter(self, client):
        await create_test_request(client)
        resp = await client.get("/api/v1/requests", params={"status": "CREATED"})
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "CREATED"


class TestGetRequest:
    """GET /api/v1/requests/{id}."""

    async def test_get_existing_request(self, client):
        created = await create_test_request(client)
        resp = await client.get(f"/api/v1/requests/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    async def test_get_nonexistent_returns_404(self, client):
        resp = await client.get(f"/api/v1/requests/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestRequestTransitions:
    """POST /api/v1/requests/{id}/transition."""

    async def test_advance_created_to_receiving(self, client):
        created = await create_test_request(client)
        resp = await client.post(
            f"/api/v1/requests/{created['id']}/transition",
            json={"target_status": "RECEIVING"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "RECEIVING"

    async def test_invalid_transition_returns_422(self, client):
        created = await create_test_request(client)
        resp = await client.post(
            f"/api/v1/requests/{created['id']}/transition",
            json={"target_status": "COMPUTING"},
        )
        assert resp.status_code == 422


class TestConfirmRequest:
    """POST /api/v1/requests/{id}/confirm."""

    async def _advance_to_staging(self, client, request_id: str):
        await client.post(
            f"/api/v1/requests/{request_id}/transition",
            json={"target_status": "RECEIVING"},
        )
        await client.post(
            f"/api/v1/requests/{request_id}/transition",
            json={"target_status": "STAGING"},
        )

    async def test_confirm_staging_to_ready(self, client):
        created = await create_test_request(client)
        await self._advance_to_staging(client, created["id"])
        resp = await client.post(
            f"/api/v1/requests/{created['id']}/confirm",
            json={"confirm_note": "All good"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "READY_TO_COMPUTE"

    async def test_confirm_auto_advances_from_created(self, client):
        """Confirm endpoint auto-advances CREATED → STAGING → READY_TO_COMPUTE."""
        created = await create_test_request(client)
        resp = await client.post(
            f"/api/v1/requests/{created['id']}/confirm",
            json={},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "READY_TO_COMPUTE"


class TestSubmitRequest:
    """POST /api/v1/requests/{id}/submit."""

    async def _advance_to_ready(self, client, request_id: str):
        await client.post(
            f"/api/v1/requests/{request_id}/transition",
            json={"target_status": "RECEIVING"},
        )
        await client.post(
            f"/api/v1/requests/{request_id}/transition",
            json={"target_status": "STAGING"},
        )
        await client.post(
            f"/api/v1/requests/{request_id}/confirm",
            json={},
        )

    async def test_submit_creates_runs(self, client):
        created = await create_test_request(client)
        await self._advance_to_ready(client, created["id"])
        resp = await client.post(f"/api/v1/requests/{created['id']}/submit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPUTING"
        assert len(data["run_ids"]) >= 1


class TestCancelRequest:
    """POST /api/v1/requests/{id}/cancel."""

    async def test_cancel_created_request(self, client):
        created = await create_test_request(client)
        resp = await client.post(
            f"/api/v1/requests/{created['id']}/cancel",
            json={"reason": "Not needed anymore"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CANCELLED"
        assert resp.json()["cancel_reason"] == "Not needed anymore"

    async def test_cancel_computing_request_returns_error(self, client):
        """Cannot cancel a request in COMPUTING status."""
        created = await create_test_request(client)
        # Advance to COMPUTING
        await client.post(
            f"/api/v1/requests/{created['id']}/transition",
            json={"target_status": "RECEIVING"},
        )
        await client.post(
            f"/api/v1/requests/{created['id']}/transition",
            json={"target_status": "STAGING"},
        )
        await client.post(
            f"/api/v1/requests/{created['id']}/confirm", json={}
        )
        await client.post(f"/api/v1/requests/{created['id']}/submit")
        resp = await client.post(
            f"/api/v1/requests/{created['id']}/cancel",
            json={"reason": "Too late"},
        )
        assert resp.status_code in (409, 422)


class TestCrossTenantIsolation:
    """Requests from one institution should not be visible to another."""

    async def test_other_institution_cannot_see_request(self, client, client_as, other_institution_user):
        created = await create_test_request(client)
        async with client_as(other_institution_user) as other_client:
            resp = await other_client.get(f"/api/v1/requests/{created['id']}")
            assert resp.status_code == 404
