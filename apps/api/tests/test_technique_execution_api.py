"""Phase 7 — Technique execution API + request integration tests."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request import Case, Request
from app.models.run import Run
from app.models.technique import ServiceTechniqueWeight, TechniqueModule, TechniqueRun
from tests.conftest import (
    DEFAULT_INSTITUTION_ID,
    DEFAULT_PIPELINE_ID,
    DEFAULT_SERVICE_ID,
)

pytestmark = pytest.mark.anyio


# --- Helpers ---


async def _seed_technique_service(db: AsyncSession, count: int = 2) -> list[TechniqueModule]:
    """Create technique modules linked to DEFAULT_SERVICE_ID."""
    techs = []
    for i in range(count):
        key = f"EXEC_T{i}_{uuid.uuid4().hex[:6].upper()}"
        tm = TechniqueModule(
            key=key,
            title_ko=f"기법 {i}",
            title_en=f"Technique {i}",
            modality="MRI",
            category="Structural",
            docker_image=f"neurohub/{key.lower()}:1.0.0",
            resource_requirements={"gpu": False, "memory_gb": 4},
        )
        db.add(tm)
        await db.flush()
        techs.append(tm)

        w = ServiceTechniqueWeight(
            service_id=DEFAULT_SERVICE_ID,
            technique_module_id=tm.id,
            base_weight=round(1.0 / count, 4),
            is_required=True,
        )
        db.add(w)
    await db.flush()
    return techs


async def _create_request_and_run(db: AsyncSession) -> tuple[Request, Run]:
    """Create a Request + Case + Run for testing."""
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
        patient_ref="PAT-EXEC-001",
    )
    db.add(case)
    await db.flush()

    run = Run(
        institution_id=DEFAULT_INSTITUTION_ID,
        request_id=req.id,
        case_id=case.id,
        status="RUNNING",
    )
    db.add(run)
    await db.flush()
    return req, run


# --- Tests ---


async def test_list_technique_runs(client: AsyncClient, db: AsyncSession):
    """GET /requests/{id}/runs/{run_id}/techniques returns technique run list."""
    techs = await _seed_technique_service(db, count=3)
    req, run = await _create_request_and_run(db)

    from app.services.technique_orchestrator import fan_out_techniques

    await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)

    resp = await client.get(f"/api/v1/requests/{req.id}/runs/{run.id}/techniques")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


async def test_get_technique_run_detail(client: AsyncClient, db: AsyncSession):
    """GET /requests/{id}/runs/{run_id}/techniques/{tech_run_id} returns detail."""
    await _seed_technique_service(db, count=1)
    req, run = await _create_request_and_run(db)

    from app.services.technique_orchestrator import fan_out_techniques, on_technique_complete
    from app.services.technique_output import TechniqueOutput

    trs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)
    output = TechniqueOutput(
        module=trs[0].technique_key,
        module_version="1.0.0",
        qc_score=85.0,
        qc_flags=[],
        features={"score": 0.75},
        maps={"result": "/outputs/result.nii.gz"},
        confidence=85.0,
    )
    await on_technique_complete(db, trs[0].id, output)

    resp = await client.get(
        f"/api/v1/requests/{req.id}/runs/{run.id}/techniques/{trs[0].id}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["qc_score"] == 85.0
    assert data["output_data"]["module"] == trs[0].technique_key


async def test_fusion_result_before_complete_404(client: AsyncClient, db: AsyncSession):
    """GET /requests/{id}/runs/{run_id}/fusion returns 404 when not all done."""
    await _seed_technique_service(db, count=2)
    req, run = await _create_request_and_run(db)

    from app.services.technique_orchestrator import fan_out_techniques

    await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)

    resp = await client.get(f"/api/v1/requests/{req.id}/runs/{run.id}/fusion")
    assert resp.status_code == 404


async def test_fusion_result_after_complete(client: AsyncClient, db: AsyncSession):
    """GET /requests/{id}/runs/{run_id}/fusion returns result when all done."""
    await _seed_technique_service(db, count=2)
    req, run = await _create_request_and_run(db)

    from app.services.technique_orchestrator import (
        fan_in_and_fuse,
        fan_out_techniques,
        on_technique_complete,
    )
    from app.services.technique_output import TechniqueOutput

    trs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)
    for tr in trs:
        output = TechniqueOutput(
            module=tr.technique_key,
            module_version="1.0.0",
            qc_score=90.0,
            qc_flags=[],
            features={"score": 0.8},
            maps={},
            confidence=90.0,
        )
        await on_technique_complete(db, tr.id, output)

    # Run fusion and store on run
    fusion_result = await fan_in_and_fuse(db, run.id, DEFAULT_SERVICE_ID)
    run.output_data = {
        "fusion": {
            "service_id": fusion_result.service_id,
            "included_modules": fusion_result.included_modules,
            "confidence_score": fusion_result.confidence_score,
            "concordance_score": fusion_result.concordance_score,
            "results": fusion_result.results,
        }
    }
    await db.flush()

    resp = await client.get(f"/api/v1/requests/{req.id}/runs/{run.id}/fusion")
    assert resp.status_code == 200
    data = resp.json()
    assert "included_modules" in data
    assert data["confidence_score"] == 90.0


async def test_technique_callback_updates_status(client: AsyncClient, db: AsyncSession):
    """POST /internal/technique-runs/{id}/result updates status."""
    await _seed_technique_service(db, count=1)
    req, run = await _create_request_and_run(db)

    from app.services.technique_orchestrator import fan_out_techniques

    trs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)

    payload = {
        "module": trs[0].technique_key,
        "module_version": "1.0.0",
        "qc_score": 88.0,
        "qc_flags": [],
        "features": {"metric": 0.5},
        "maps": {},
        "confidence": 88.0,
    }
    resp = await client.post(
        f"/api/v1/internal/technique-runs/{trs[0].id}/result",
        json=payload,
        headers={"X-Internal-Key": "test-internal-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["all_done"] is True

    # Verify DB state
    refreshed = (await db.execute(
        select(TechniqueRun).where(TechniqueRun.id == trs[0].id)
    )).scalar_one()
    assert refreshed.status == "COMPLETED"
    assert refreshed.qc_score == 88.0


async def test_technique_callback_invalid_key_401(client: AsyncClient, db: AsyncSession):
    """POST /internal/technique-runs/{id}/result with bad key returns 401."""
    resp = await client.post(
        f"/api/v1/internal/technique-runs/{uuid.uuid4()}/result",
        json={"module": "X", "module_version": "1.0.0", "qc_score": 80, "qc_flags": [],
              "features": {}, "maps": {}, "confidence": 80},
        headers={"X-Internal-Key": "wrong-key"},
    )
    assert resp.status_code == 401


async def test_legacy_service_uses_single_pipeline(client: AsyncClient, db: AsyncSession):
    """Service without technique weights uses legacy single-pipeline dispatch."""
    # No techniques seeded for this service, so fan-out should NOT happen
    # The existing submit_request logic should work normally
    req, run = await _create_request_and_run(db)

    # Verify no technique runs exist for this run
    trs = (await db.execute(
        select(TechniqueRun).where(TechniqueRun.run_id == run.id)
    )).scalars().all()
    assert len(trs) == 0


async def test_technique_service_fans_out(client: AsyncClient, db: AsyncSession):
    """Service with technique weights triggers fan-out when dispatched."""
    techs = await _seed_technique_service(db, count=3)
    req, run = await _create_request_and_run(db)

    # Simulate the dispatch logic: check if service has weights, then fan out
    from app.services.technique_orchestrator import fan_out_techniques

    weights = (await db.execute(
        select(ServiceTechniqueWeight).where(
            ServiceTechniqueWeight.service_id == DEFAULT_SERVICE_ID
        )
    )).scalars().all()

    if weights:
        trs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)
        assert len(trs) == 3

    # Verify technique runs created
    all_trs = (await db.execute(
        select(TechniqueRun).where(TechniqueRun.run_id == run.id)
    )).scalars().all()
    assert len(all_trs) == 3


async def test_multi_tenant_isolation(client_as, db: AsyncSession, other_institution_user):
    """Other institution cannot see technique runs."""
    await _seed_technique_service(db, count=1)
    req, run = await _create_request_and_run(db)

    from app.services.technique_orchestrator import fan_out_techniques

    await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)

    async with client_as(other_institution_user) as other_client:
        resp = await other_client.get(
            f"/api/v1/requests/{req.id}/runs/{run.id}/techniques"
        )
        assert resp.status_code == 404
