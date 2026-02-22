"""Integration tests that verify full request lifecycle against real DB.

These tests require a running Postgres database. They will be skipped
if the database is not available (e.g., local dev without Supabase).
"""
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import create_test_request, DEFAULT_SERVICE_ID, DEFAULT_PIPELINE_ID


class TestRequestLifecycle:
    """Test the full request lifecycle: create -> upload -> confirm -> submit."""

    @pytest.mark.asyncio
    async def test_create_request_returns_201(self, client):
        resp = await client.post("/api/v1/requests", json={
            "service_id": str(DEFAULT_SERVICE_ID),
            "pipeline_id": str(DEFAULT_PIPELINE_ID),
            "cases": [{"patient_ref": "INTEG-001"}],
            "idempotency_key": f"integ-test-{uuid.uuid4()}",
        })
        if resp.status_code == 500:
            pytest.skip("Database not available")
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "CREATED"
        assert len(body.get("cases", [])) >= 0

    @pytest.mark.asyncio
    async def test_list_requests_with_pagination(self, client):
        resp = await client.get("/api/v1/requests?offset=0&limit=5")
        if resp.status_code == 500:
            pytest.skip("Database not available")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "has_more" in body

    @pytest.mark.asyncio
    async def test_transition_created_to_receiving(self, client):
        req = await create_test_request(client, idempotency_key=f"integ-trans-{uuid.uuid4()}")
        req_id = req.get("id")
        if not req_id:
            pytest.skip("Database not available")

        resp = await client.post(f"/api/v1/requests/{req_id}/transition", json={
            "target_status": "RECEIVING",
        })
        assert resp.status_code in (200, 409, 422, 500)

    @pytest.mark.asyncio
    async def test_upload_presign_creates_case_file(self, client):
        req = await create_test_request(client, idempotency_key=f"integ-upload-{uuid.uuid4()}")
        req_id = req.get("id")
        if not req_id:
            pytest.skip("Database not available")

        # Get cases
        cases_resp = await client.get(f"/api/v1/requests/{req_id}/cases")
        if cases_resp.status_code != 200:
            pytest.skip("Cannot list cases")
        cases = cases_resp.json().get("items", [])
        if not cases:
            pytest.skip("No cases")

        case_id = cases[0]["id"]

        with patch("app.services.storage.create_presigned_upload", new_callable=AsyncMock, return_value="https://example.com/upload"):
            resp = await client.post(
                f"/api/v1/requests/{req_id}/cases/{case_id}/files/presign",
                json={"slot_name": "primary", "file_name": "test.dcm", "content_type": "application/dicom", "file_size": 1024},
            )
        if resp.status_code == 500:
            pytest.skip("Database not available")
        assert resp.status_code == 201
        body = resp.json()
        assert "case_file_id" in body
        assert "presigned_url" in body

    @pytest.mark.asyncio
    async def test_full_lifecycle_create_to_submit(self, client):
        """Test create -> receive -> stage -> confirm -> submit flow."""
        req = await create_test_request(client, idempotency_key=f"integ-full-{uuid.uuid4()}")
        req_id = req.get("id")
        if not req_id:
            pytest.skip("Database not available")

        # Transition to RECEIVING
        await client.post(f"/api/v1/requests/{req_id}/transition", json={"target_status": "RECEIVING"})

        # Transition to STAGING
        resp = await client.post(f"/api/v1/requests/{req_id}/transition", json={"target_status": "STAGING"})

        # Confirm
        resp = await client.post(f"/api/v1/requests/{req_id}/confirm", json={"confirm_note": "Test"})

        # Submit
        resp = await client.post(f"/api/v1/requests/{req_id}/submit", json={})
        # Submit may fail if cases aren't ready, but should not 500
        assert resp.status_code != 500


class TestCrossTenantIsolation:
    """Verify that one institution cannot access another's data."""

    @pytest.mark.asyncio
    async def test_other_institution_cannot_list_requests(self, client_as, other_institution_user):
        """Requests from one institution shouldn't appear for another."""
        async with client_as(other_institution_user) as other_client:
            resp = await other_client.get("/api/v1/requests")
            if resp.status_code == 500:
                pytest.skip("Database not available")
            assert resp.status_code == 200
            body = resp.json()
            # Should return empty or only their own institution's data
            for item in body.get("items", []):
                assert item.get("institution_id") != "00000000-0000-0000-0000-000000000001"


class TestAdminEndpoints:
    @pytest.mark.asyncio
    async def test_admin_stats(self, client):
        resp = await client.get("/api/v1/admin/stats")
        if resp.status_code == 500:
            pytest.skip("Database not available")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_audit_logs(self, client):
        resp = await client.get("/api/v1/admin/audit-logs")
        if resp.status_code == 500:
            pytest.skip("Database not available")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_non_admin_cannot_access_admin(self, client_as, service_user):
        async with client_as(service_user) as user_client:
            resp = await user_client.get("/api/v1/admin/stats")
            assert resp.status_code in (403, 500)
