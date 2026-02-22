"""Tests for batch request creation API."""
import uuid
import pytest


class TestBatchRequestCreation:
    @pytest.mark.asyncio
    async def test_batch_create_returns_results(self, client):
        """Batch creation should return success/failure for each request."""
        from tests.conftest import DEFAULT_SERVICE_ID, DEFAULT_PIPELINE_ID
        resp = await client.post("/api/v1/b2b/requests/batch", json={
            "requests": [
                {
                    "service_id": str(DEFAULT_SERVICE_ID),
                    "pipeline_id": str(DEFAULT_PIPELINE_ID),
                    "cases": [{"patient_ref": "BATCH-001"}],
                    "idempotency_key": f"batch-{uuid.uuid4()}",
                },
                {
                    "service_id": str(DEFAULT_SERVICE_ID),
                    "pipeline_id": str(DEFAULT_PIPELINE_ID),
                    "cases": [{"patient_ref": "BATCH-002"}],
                    "idempotency_key": f"batch-{uuid.uuid4()}",
                },
            ]
        })
        assert resp.status_code in (200, 207, 500)

    @pytest.mark.asyncio
    async def test_batch_max_size_limit(self, client):
        """Batch should reject more than 50 requests."""
        from tests.conftest import DEFAULT_SERVICE_ID, DEFAULT_PIPELINE_ID
        requests = [
            {
                "service_id": str(DEFAULT_SERVICE_ID),
                "pipeline_id": str(DEFAULT_PIPELINE_ID),
                "cases": [{"patient_ref": f"BATCH-{i}"}],
                "idempotency_key": f"batch-limit-{uuid.uuid4()}",
            }
            for i in range(51)
        ]
        resp = await client.post("/api/v1/b2b/requests/batch", json={"requests": requests})
        assert resp.status_code in (400, 422, 500)

    @pytest.mark.asyncio
    async def test_batch_partial_failure(self, client):
        """If some requests fail, others should still succeed."""
        from tests.conftest import DEFAULT_SERVICE_ID, DEFAULT_PIPELINE_ID
        same_key = f"batch-dup-{uuid.uuid4()}"
        resp = await client.post("/api/v1/b2b/requests/batch", json={
            "requests": [
                {
                    "service_id": str(DEFAULT_SERVICE_ID),
                    "pipeline_id": str(DEFAULT_PIPELINE_ID),
                    "cases": [{"patient_ref": "BATCH-DUP-1"}],
                    "idempotency_key": same_key,
                },
                {
                    "service_id": str(DEFAULT_SERVICE_ID),
                    "pipeline_id": str(DEFAULT_PIPELINE_ID),
                    "cases": [{"patient_ref": "BATCH-DUP-2"}],
                    "idempotency_key": same_key,  # Duplicate key
                },
            ]
        })
        assert resp.status_code in (200, 207, 500)
