"""Phase 6 — Technique orchestrator (fan-out / fan-in) tests."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import Run
from app.models.request import Case, Request
from app.models.technique import ServiceTechniqueWeight, TechniqueModule, TechniqueRun
from app.services.technique_orchestrator import (
    fan_in_and_fuse,
    fan_out_techniques,
    mark_technique_failed,
    on_technique_complete,
)
from app.services.technique_output import TechniqueOutput
from tests.conftest import DEFAULT_INSTITUTION_ID, DEFAULT_PIPELINE_ID, DEFAULT_SERVICE_ID

pytestmark = pytest.mark.anyio


# --- Helpers ---

async def _seed_techniques_and_weights(db: AsyncSession, count: int = 3) -> list[TechniqueModule]:
    """Create N technique modules and link them to DEFAULT_SERVICE_ID with equal weights."""
    techs = []
    for i in range(count):
        key = f"ORCH_T{i}_{uuid.uuid4().hex[:6].upper()}"
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


async def _create_run(db: AsyncSession) -> Run:
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
        patient_ref="PAT-ORCH-001",
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
    return run


def _make_output(key: str, qc: float = 85.0) -> TechniqueOutput:
    return TechniqueOutput(
        module=key,
        module_version="1.0.0",
        qc_score=qc,
        qc_flags=[],
        features={"score": 0.75},
        maps={"result_map": f"/outputs/{key}.nii.gz"},
        confidence=qc,
    )


# --- Tests ---


async def test_fan_out_creates_one_run_per_technique(db: AsyncSession):
    techs = await _seed_techniques_and_weights(db, count=4)
    run = await _create_run(db)

    technique_runs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)
    assert len(technique_runs) == 4


async def test_fan_out_status_all_pending(db: AsyncSession):
    await _seed_techniques_and_weights(db, count=2)
    run = await _create_run(db)

    technique_runs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)
    assert all(tr.status == "PENDING" for tr in technique_runs)


async def test_fan_out_builds_per_technique_job_spec(db: AsyncSession):
    techs = await _seed_techniques_and_weights(db, count=1)
    run = await _create_run(db)

    technique_runs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)
    assert len(technique_runs) == 1
    spec = technique_runs[0].job_spec
    assert spec["docker_image"] == techs[0].docker_image
    assert spec["technique_key"] == techs[0].key


async def test_on_complete_updates_status(db: AsyncSession):
    techs = await _seed_techniques_and_weights(db, count=1)
    run = await _create_run(db)
    trs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)

    output = _make_output(trs[0].technique_key)
    all_done = await on_technique_complete(db, trs[0].id, output)

    assert all_done is True
    refreshed = (await db.execute(
        select(TechniqueRun).where(TechniqueRun.id == trs[0].id)
    )).scalar_one()
    assert refreshed.status == "COMPLETED"
    assert refreshed.qc_score == 85.0
    assert refreshed.output_data["module"] == trs[0].technique_key


async def test_on_complete_false_when_pending_remain(db: AsyncSession):
    await _seed_techniques_and_weights(db, count=3)
    run = await _create_run(db)
    trs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)

    # Complete only the first
    output = _make_output(trs[0].technique_key)
    all_done = await on_technique_complete(db, trs[0].id, output)
    assert all_done is False


async def test_on_complete_true_when_all_done(db: AsyncSession):
    await _seed_techniques_and_weights(db, count=2)
    run = await _create_run(db)
    trs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)

    for tr in trs:
        output = _make_output(tr.technique_key)
        result = await on_technique_complete(db, tr.id, output)

    assert result is True


async def test_fan_in_calls_fusion_engine(db: AsyncSession):
    techs = await _seed_techniques_and_weights(db, count=2)
    run = await _create_run(db)
    trs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)

    for tr in trs:
        output = _make_output(tr.technique_key, qc=90)
        await on_technique_complete(db, tr.id, output)

    fusion_result = await fan_in_and_fuse(db, run.id, DEFAULT_SERVICE_ID)
    assert len(fusion_result.included_modules) == 2
    assert fusion_result.confidence_score == 90.0


async def test_fan_in_stores_result(db: AsyncSession):
    techs = await _seed_techniques_and_weights(db, count=2)
    run = await _create_run(db)
    trs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)

    for tr in trs:
        output = _make_output(tr.technique_key)
        await on_technique_complete(db, tr.id, output)

    fusion_result = await fan_in_and_fuse(db, run.id, DEFAULT_SERVICE_ID)
    assert fusion_result.service_id == str(DEFAULT_SERVICE_ID)
    assert "score" in fusion_result.results


async def test_fan_out_skips_deprecated_techniques(db: AsyncSession):
    techs = await _seed_techniques_and_weights(db, count=3)
    # Deprecate one
    techs[0].status = "DEPRECATED"
    await db.flush()

    run = await _create_run(db)
    trs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)
    keys = {tr.technique_key for tr in trs}
    assert techs[0].key not in keys
    assert len(trs) == 2


async def test_failed_technique_excluded_from_fusion(db: AsyncSession):
    techs = await _seed_techniques_and_weights(db, count=3)
    run = await _create_run(db)
    trs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)

    # First fails
    await mark_technique_failed(db, trs[0].id, "container crashed")
    # Others complete
    for tr in trs[1:]:
        output = _make_output(tr.technique_key, qc=80)
        await on_technique_complete(db, tr.id, output)

    fusion_result = await fan_in_and_fuse(db, run.id, DEFAULT_SERVICE_ID)
    assert trs[0].technique_key not in fusion_result.included_modules
    assert len(fusion_result.included_modules) == 2


async def test_all_techniques_failed_raises(db: AsyncSession):
    techs = await _seed_techniques_and_weights(db, count=2)
    run = await _create_run(db)
    trs = await fan_out_techniques(db, run.id, DEFAULT_SERVICE_ID)

    for tr in trs:
        await mark_technique_failed(db, tr.id, "all crashed")

    with pytest.raises(ValueError, match="All technique runs failed"):
        await fan_in_and_fuse(db, run.id, DEFAULT_SERVICE_ID)
