"""Tests for pipeline status and technique run endpoints.

Covers:
- GET /api/v1/requests/{id}/pipeline-status
- GET /api/v1/requests/{id}/technique-runs
- GET /api/v1/admin/requests with search param
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request import Case, Request
from app.models.run import Run
from app.models.technique import ServiceTechniqueWeight, TechniqueModule, TechniqueRun
from tests.conftest import (
    DEFAULT_INSTITUTION_ID,
    DEFAULT_PIPELINE_ID,
    DEFAULT_SERVICE_ID,
    create_test_request,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_request_in_computing(db: AsyncSession) -> tuple[Request, Case]:
    """Insert a Request + Case in COMPUTING status directly into the DB."""
    req = Request(
        institution_id=DEFAULT_INSTITUTION_ID,
        service_id=DEFAULT_SERVICE_ID,
        pipeline_id=DEFAULT_PIPELINE_ID,
        status="COMPUTING",
    )
    db.add(req)
    await db.flush()

    case = Case(
        request_id=req.id,
        institution_id=DEFAULT_INSTITUTION_ID,
        patient_ref="PAT-PIPE-001",
        status="READY",
    )
    db.add(case)
    await db.flush()
    return req, case


async def _create_run(db: AsyncSession, req: Request, case: Case, status: str = "RUNNING") -> Run:
    """Insert a Run for the given request/case."""
    run = Run(
        institution_id=DEFAULT_INSTITUTION_ID,
        request_id=req.id,
        case_id=case.id,
        status=status,
    )
    db.add(run)
    await db.flush()
    return run


async def _seed_technique_and_weight(db: AsyncSession, key_suffix: str = "") -> TechniqueModule:
    """Create a TechniqueModule + ServiceTechniqueWeight linked to DEFAULT_SERVICE_ID."""
    key = f"PIPE_T_{uuid.uuid4().hex[:8].upper()}{key_suffix}"
    tm = TechniqueModule(
        key=key,
        title_ko=f"파이프라인 기법 {key}",
        title_en=f"Pipeline Technique {key}",
        modality="MRI",
        category="Structural",
        docker_image=f"neurohub/{key.lower()}:1.0.0",
    )
    db.add(tm)
    await db.flush()

    w = ServiceTechniqueWeight(
        service_id=DEFAULT_SERVICE_ID,
        technique_module_id=tm.id,
        base_weight=0.5,
        is_required=True,
    )
    db.add(w)
    await db.flush()
    return tm


async def _create_technique_run(
    db: AsyncSession,
    run: Run,
    tm: TechniqueModule,
    status: str = "COMPLETED",
    qc_score: float | None = 85.0,
) -> TechniqueRun:
    """Insert a TechniqueRun for the given run and TechniqueModule."""
    tr = TechniqueRun(
        run_id=run.id,
        technique_module_id=tm.id,
        technique_key=tm.key,
        status=status,
        qc_score=qc_score if status == "COMPLETED" else None,
        output_data={"features": {"vol": 1.2}} if status == "COMPLETED" else None,
    )
    db.add(tr)
    await db.flush()
    return tr


# ---------------------------------------------------------------------------
# GET /api/v1/requests/{id}/pipeline-status
# ---------------------------------------------------------------------------


class TestPipelineStatus:
    """Tests for GET /api/v1/requests/{id}/pipeline-status."""

    async def test_not_found_returns_404(self, client: AsyncClient):
        """Non-existent request returns 404."""
        resp = await client.get(f"/api/v1/requests/{uuid.uuid4()}/pipeline-status")
        assert resp.status_code == 404

    async def test_no_runs_returns_empty_summary(self, client: AsyncClient, db: AsyncSession):
        """Request with no runs returns empty runs list and zero technique_summary."""
        req, _case = await _create_request_in_computing(db)

        resp = await client.get(f"/api/v1/requests/{req.id}/pipeline-status")
        assert resp.status_code == 200
        data = resp.json()

        assert data["request_id"] == str(req.id)
        assert data["request_status"] == "COMPUTING"
        assert data["runs"] == []
        summary = data["technique_summary"]
        assert summary["total"] == 0
        assert summary["pending"] == 0
        assert summary["running"] == 0
        assert summary["completed"] == 0
        assert summary["failed"] == 0

    async def test_with_runs_and_technique_runs(self, client: AsyncClient, db: AsyncSession):
        """Pipeline status includes runs and their technique runs."""
        tm = await _seed_technique_and_weight(db)
        req, case = await _create_request_in_computing(db)
        run = await _create_run(db, req, case, status="RUNNING")
        tr = await _create_technique_run(db, run, tm, status="COMPLETED", qc_score=90.0)

        resp = await client.get(f"/api/v1/requests/{req.id}/pipeline-status")
        assert resp.status_code == 200
        data = resp.json()

        assert data["request_id"] == str(req.id)
        assert len(data["runs"]) == 1

        run_data = data["runs"][0]
        assert run_data["id"] == str(run.id)
        assert run_data["status"] == "RUNNING"
        assert len(run_data["technique_runs"]) == 1

        tr_data = run_data["technique_runs"][0]
        assert tr_data["id"] == str(tr.id)
        assert tr_data["technique_key"] == tm.key
        assert tr_data["status"] == "COMPLETED"
        assert tr_data["qc_score"] == 90.0

    async def test_technique_summary_counts_correctly(self, client: AsyncClient, db: AsyncSession):
        """Technique summary aggregates counts across all runs."""
        tm1 = await _seed_technique_and_weight(db, "_A")
        tm2 = await _seed_technique_and_weight(db, "_B")
        req, case = await _create_request_in_computing(db)
        run = await _create_run(db, req, case, status="RUNNING")

        await _create_technique_run(db, run, tm1, status="COMPLETED", qc_score=85.0)
        await _create_technique_run(db, run, tm2, status="RUNNING", qc_score=None)

        resp = await client.get(f"/api/v1/requests/{req.id}/pipeline-status")
        assert resp.status_code == 200
        summary = resp.json()["technique_summary"]

        assert summary["total"] == 2
        assert summary["completed"] == 1
        assert summary["running"] == 1

    async def test_multiple_runs_all_appear(self, client: AsyncClient, db: AsyncSession):
        """Requests with multiple cases (multiple runs) return all runs."""
        tm = await _seed_technique_and_weight(db, "_MULTI")
        req, case1 = await _create_request_in_computing(db)

        case2 = Case(
            request_id=req.id,
            institution_id=DEFAULT_INSTITUTION_ID,
            patient_ref="PAT-PIPE-002",
            status="READY",
        )
        db.add(case2)
        await db.flush()

        run1 = await _create_run(db, req, case1, status="COMPLETED")
        run2 = await _create_run(db, req, case2, status="RUNNING")
        await _create_technique_run(db, run1, tm, status="COMPLETED", qc_score=80.0)

        resp = await client.get(f"/api/v1/requests/{req.id}/pipeline-status")
        assert resp.status_code == 200
        data = resp.json()

        run_ids = {r["id"] for r in data["runs"]}
        assert str(run1.id) in run_ids
        assert str(run2.id) in run_ids

    async def test_cross_tenant_isolation(
        self, client_as, db: AsyncSession, other_institution_user
    ):
        """Other institution cannot see another institution's pipeline status."""
        req, _case = await _create_request_in_computing(db)

        async with client_as(other_institution_user) as other_client:
            resp = await other_client.get(f"/api/v1/requests/{req.id}/pipeline-status")
            assert resp.status_code == 404

    async def test_failed_technique_counted_in_summary(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Failed technique runs are counted in the failed bucket."""
        tm = await _seed_technique_and_weight(db, "_FAIL")
        req, case = await _create_request_in_computing(db)
        run = await _create_run(db, req, case, status="FAILED")
        await _create_technique_run(db, run, tm, status="FAILED", qc_score=None)

        resp = await client.get(f"/api/v1/requests/{req.id}/pipeline-status")
        assert resp.status_code == 200
        summary = resp.json()["technique_summary"]
        assert summary["total"] == 1
        assert summary["failed"] == 1


# ---------------------------------------------------------------------------
# GET /api/v1/requests/{id}/technique-runs
# ---------------------------------------------------------------------------


class TestTechniqueRunsList:
    """Tests for GET /api/v1/requests/{id}/technique-runs."""

    async def test_not_found_returns_404(self, client: AsyncClient):
        """Non-existent request returns 404."""
        resp = await client.get(f"/api/v1/requests/{uuid.uuid4()}/technique-runs")
        assert resp.status_code == 404

    async def test_empty_when_no_runs(self, client: AsyncClient, db: AsyncSession):
        """Request with no runs returns empty items list."""
        req, _case = await _create_request_in_computing(db)

        resp = await client.get(f"/api/v1/requests/{req.id}/technique-runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_returns_technique_runs_for_request(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Returns all technique runs across all runs for the request."""
        tm = await _seed_technique_and_weight(db, "_TR")
        req, case = await _create_request_in_computing(db)
        run = await _create_run(db, req, case, status="RUNNING")
        tr = await _create_technique_run(db, run, tm, status="COMPLETED", qc_score=88.0)

        resp = await client.get(f"/api/v1/requests/{req.id}/technique-runs")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total"] == 1
        assert len(data["items"]) == 1

        item = data["items"][0]
        assert item["id"] == str(tr.id)
        assert item["run_id"] == str(run.id)
        assert item["case_id"] == str(case.id)
        assert item["technique_key"] == tm.key
        assert item["status"] == "COMPLETED"
        assert item["qc_score"] == 88.0

    async def test_aggregates_across_multiple_runs(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Technique runs from multiple runs (cases) are all returned."""
        tm1 = await _seed_technique_and_weight(db, "_AGG1")
        tm2 = await _seed_technique_and_weight(db, "_AGG2")
        req, case1 = await _create_request_in_computing(db)

        case2 = Case(
            request_id=req.id,
            institution_id=DEFAULT_INSTITUTION_ID,
            patient_ref="PAT-AGG-002",
            status="READY",
        )
        db.add(case2)
        await db.flush()

        run1 = await _create_run(db, req, case1, status="COMPLETED")
        run2 = await _create_run(db, req, case2, status="RUNNING")

        await _create_technique_run(db, run1, tm1, status="COMPLETED", qc_score=80.0)
        await _create_technique_run(db, run2, tm2, status="RUNNING", qc_score=None)

        resp = await client.get(f"/api/v1/requests/{req.id}/technique-runs")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total"] == 2
        technique_keys = {item["technique_key"] for item in data["items"]}
        assert tm1.key in technique_keys
        assert tm2.key in technique_keys

    async def test_output_data_included_when_completed(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Completed technique runs include output_data in the response."""
        tm = await _seed_technique_and_weight(db, "_OUT")
        req, case = await _create_request_in_computing(db)
        run = await _create_run(db, req, case, status="COMPLETED")
        await _create_technique_run(db, run, tm, status="COMPLETED", qc_score=92.0)

        resp = await client.get(f"/api/v1/requests/{req.id}/technique-runs")
        assert resp.status_code == 200
        item = resp.json()["items"][0]

        assert item["output_data"] is not None
        assert "features" in item["output_data"]

    async def test_cross_tenant_isolation(
        self, client_as, db: AsyncSession, other_institution_user
    ):
        """Other institution cannot list technique runs for another institution's request."""
        req, _case = await _create_request_in_computing(db)

        async with client_as(other_institution_user) as other_client:
            resp = await other_client.get(f"/api/v1/requests/{req.id}/technique-runs")
            assert resp.status_code == 404

    async def test_pending_technique_has_null_fields(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Pending/running technique runs have null timestamps and qc_score."""
        tm = await _seed_technique_and_weight(db, "_PEND")
        req, case = await _create_request_in_computing(db)
        run = await _create_run(db, req, case, status="RUNNING")
        await _create_technique_run(db, run, tm, status="RUNNING", qc_score=None)

        resp = await client.get(f"/api/v1/requests/{req.id}/technique-runs")
        assert resp.status_code == 200
        item = resp.json()["items"][0]

        assert item["status"] == "RUNNING"
        assert item["qc_score"] is None
        assert item["output_data"] is None
        assert item["completed_at"] is None


# ---------------------------------------------------------------------------
# GET /api/v1/admin/requests with search + filter
# ---------------------------------------------------------------------------


class TestAdminRequestsSearch:
    """Tests for GET /api/v1/admin/requests with search and status filter params."""

    async def test_list_returns_paginated_shape(self, client: AsyncClient):
        """Admin list returns items/total/offset/limit/has_more."""
        resp = await client.get("/api/v1/admin/requests")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert "has_more" in data

    async def test_search_param_accepted(self, client: AsyncClient):
        """search query param is accepted without error."""
        resp = await client.get("/api/v1/admin/requests?search=abc")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_search_with_status_filter(self, client: AsyncClient):
        """search and status can be combined."""
        resp = await client.get("/api/v1/admin/requests?search=abc&status=CREATED")
        assert resp.status_code == 200

    async def test_search_returns_matching_requests(
        self, client: AsyncClient, db: AsyncSession
    ):
        """Searching by request UUID prefix returns that request."""
        req, _case = await _create_request_in_computing(db)
        # Search using the first 8 chars of the UUID
        prefix = str(req.id)[:8]

        resp = await client.get(f"/api/v1/admin/requests?search={prefix}")
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["id"] for item in data["items"]]
        assert str(req.id) in ids

    async def test_search_no_match_returns_empty(self, client: AsyncClient):
        """Search with a nonsense string returns empty items list."""
        resp = await client.get("/api/v1/admin/requests?search=xyznonexistent999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_status_filter_created(self, client: AsyncClient, db: AsyncSession):
        """Status filter returns only requests with the matching status."""
        # Create a CREATED status request via the API helper
        created = await create_test_request(client)
        assert created.get("status") == "CREATED"

        resp = await client.get("/api/v1/admin/requests?status=CREATED")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["status"] == "CREATED"

    async def test_status_filter_computing(self, client: AsyncClient, db: AsyncSession):
        """Status filter for COMPUTING returns only computing requests."""
        req, _case = await _create_request_in_computing(db)

        resp = await client.get("/api/v1/admin/requests?status=COMPUTING")
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["id"] for item in data["items"]]
        assert str(req.id) in ids
        for item in data["items"]:
            assert item["status"] == "COMPUTING"

    async def test_pagination_offset_and_limit(self, client: AsyncClient, db: AsyncSession):
        """offset and limit params are respected."""
        # Create two requests so we have at least some data
        await _create_request_in_computing(db)
        await _create_request_in_computing(db)

        resp = await client.get("/api/v1/admin/requests?offset=0&limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 1
        assert data["limit"] == 1
        assert data["offset"] == 0

    async def test_non_admin_gets_forbidden(self, client_as, db: AsyncSession, service_user):
        """Non-admin role cannot access admin/requests."""
        async with client_as(service_user) as c:
            resp = await c.get("/api/v1/admin/requests")
            assert resp.status_code == 403
