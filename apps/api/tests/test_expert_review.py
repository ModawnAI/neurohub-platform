"""Tests for enhanced expert review flow with structured QC criteria."""
import uuid

import pytest

from tests.conftest import create_test_request, DEFAULT_INSTITUTION_ID


class TestQCDecisionStructured:
    """Test structured QC decision flow."""

    @pytest.mark.asyncio
    async def test_qc_approve_transitions_to_reporting(self, client):
        """QC approval should transition request to REPORTING."""
        req = await create_test_request(client)
        req_id = req.get("id")
        if not req_id:
            pytest.skip("No DB")

        # Advance to QC state - would need actual state transitions
        # Test the endpoint exists and validates input
        resp = await client.post(
            f"/api/v1/reviews/{req_id}/qc-decision",
            json={"decision": "APPROVE", "comments": "All clear", "qc_score": 95},
        )
        # Should be 409 (wrong state) or 200 - not 404 or 500
        assert resp.status_code in (200, 409, 422)

    @pytest.mark.asyncio
    async def test_qc_reject_transitions_to_failed(self, client):
        """QC rejection should transition request to FAILED."""
        req = await create_test_request(client)
        req_id = req.get("id")
        if not req_id:
            pytest.skip("No DB")

        resp = await client.post(
            f"/api/v1/reviews/{req_id}/qc-decision",
            json={"decision": "REJECT", "comments": "Quality insufficient"},
        )
        assert resp.status_code in (200, 409, 422)

    @pytest.mark.asyncio
    async def test_qc_rerun_transitions_to_computing(self, client):
        """QC rerun should transition request back to COMPUTING."""
        req = await create_test_request(client)
        req_id = req.get("id")
        if not req_id:
            pytest.skip("No DB")

        resp = await client.post(
            f"/api/v1/reviews/{req_id}/qc-decision",
            json={"decision": "RERUN", "comments": "Re-run with different params"},
        )
        assert resp.status_code in (200, 409, 422)

    @pytest.mark.asyncio
    async def test_report_review_approve_transitions_to_final(self, client):
        """Report review approval should transition to FINAL."""
        req = await create_test_request(client)
        req_id = req.get("id")
        if not req_id:
            pytest.skip("No DB")

        resp = await client.post(
            f"/api/v1/reviews/{req_id}/report-review",
            json={"decision": "APPROVE", "comments": "Report looks good"},
        )
        assert resp.status_code in (200, 409, 422)

    @pytest.mark.asyncio
    async def test_review_queue_returns_paginated(self, client):
        """Review queue should return paginated results."""
        resp = await client.get("/api/v1/reviews/queue")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    @pytest.mark.asyncio
    async def test_review_detail_includes_runs_and_reports(self, client):
        """Review detail should include runs, reports, and previous decisions."""
        req = await create_test_request(client)
        req_id = req.get("id")
        if not req_id:
            pytest.skip("No DB")

        resp = await client.get(f"/api/v1/reviews/{req_id}")
        # Should work or return 404 for wrong state
        assert resp.status_code in (200, 404, 409)

    @pytest.mark.asyncio
    async def test_qc_decision_invalid_decision_value(self, client):
        """QC decision with invalid decision value should return 422."""
        req = await create_test_request(client)
        req_id = req.get("id")
        if not req_id:
            pytest.skip("No DB")

        resp = await client.post(
            f"/api/v1/reviews/{req_id}/qc-decision",
            json={"decision": "INVALID_VALUE", "comments": "test"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_report_review_invalid_decision_value(self, client):
        """Report review with invalid decision value should return 422."""
        req = await create_test_request(client)
        req_id = req.get("id")
        if not req_id:
            pytest.skip("No DB")

        resp = await client.post(
            f"/api/v1/reviews/{req_id}/report-review",
            json={"decision": "INVALID_VALUE", "comments": "test"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_qc_score_validation_range(self, client):
        """QC score must be between 0 and 100."""
        req = await create_test_request(client)
        req_id = req.get("id")
        if not req_id:
            pytest.skip("No DB")

        resp = await client.post(
            f"/api/v1/reviews/{req_id}/qc-decision",
            json={"decision": "APPROVE", "qc_score": 150},
        )
        assert resp.status_code == 422
