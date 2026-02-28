"""Phase 1 — TechniqueModule model unit tests (written FIRST, TDD)."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.anyio


async def _make_technique(session: AsyncSession, **overrides) -> "TechniqueModule":
    from app.models.technique import TechniqueModule

    defaults = {
        "key": f"TEST_{uuid.uuid4().hex[:8].upper()}",
        "title_ko": "테스트 기법",
        "title_en": "Test Technique",
        "modality": "MRI",
        "category": "Structural",
        "docker_image": "neurohub/test:latest",
    }
    defaults.update(overrides)
    tm = TechniqueModule(**defaults)
    session.add(tm)
    await session.flush()
    return tm


async def test_technique_module_create_and_query(db: AsyncSession):
    """Insert a TechniqueModule and verify all fields round-trip."""
    from app.models.technique import TechniqueModule

    tm = await _make_technique(
        db,
        key="FDG_PET",
        title_ko="FDG PET 분석",
        title_en="FDG PET Analysis",
        modality="PET",
        category="Metabolic",
        description="FDG-PET 대사 영상 분석",
        docker_image="neurohub/fdg-pet:1.0.0",
        version="1.0.0",
        qc_config={"min_suvr": 0.5, "motion_threshold": 3.0},
        output_schema={"fields": ["suvr_map", "regional_values"]},
        resource_requirements={"gpu": True, "memory_gb": 8, "cpus": 4},
    )

    row = (await db.execute(
        select(TechniqueModule).where(TechniqueModule.key == "FDG_PET")
    )).scalar_one()

    assert row.id == tm.id
    assert row.key == "FDG_PET"
    assert row.title_ko == "FDG PET 분석"
    assert row.title_en == "FDG PET Analysis"
    assert row.modality == "PET"
    assert row.category == "Metabolic"
    assert row.description == "FDG-PET 대사 영상 분석"
    assert row.docker_image == "neurohub/fdg-pet:1.0.0"
    assert row.version == "1.0.0"
    assert row.qc_config["min_suvr"] == 0.5
    assert row.output_schema["fields"] == ["suvr_map", "regional_values"]
    assert row.resource_requirements["gpu"] is True


async def test_technique_module_unique_key_constraint(db: AsyncSession):
    """Inserting two TechniqueModules with the same key raises IntegrityError."""
    await _make_technique(db, key="DUPLICATE_KEY")
    with pytest.raises(IntegrityError):
        await _make_technique(db, key="DUPLICATE_KEY")
    await db.rollback()


async def test_technique_module_qc_config_stored_as_jsonb(db: AsyncSession):
    """Complex nested dict round-trips correctly via JSONB column."""
    complex_config = {
        "metrics": {
            "snr": {"threshold": 20.0, "weight": 0.4},
            "motion": {"threshold": 2.0, "weight": 0.3, "sub_checks": ["x", "y", "z"]},
        },
        "pass_score": 60,
        "flags": ["LOW_SNR", "HIGH_MOTION", "ARTIFACT"],
    }
    tm = await _make_technique(db, qc_config=complex_config)

    from app.models.technique import TechniqueModule
    from sqlalchemy import select

    row = (await db.execute(
        select(TechniqueModule).where(TechniqueModule.id == tm.id)
    )).scalar_one()

    assert row.qc_config == complex_config
    assert row.qc_config["metrics"]["motion"]["sub_checks"] == ["x", "y", "z"]


async def test_technique_module_default_status_is_active(db: AsyncSession):
    """A TechniqueModule created without explicit status defaults to ACTIVE."""
    tm = await _make_technique(db)
    assert tm.status == "ACTIVE"
