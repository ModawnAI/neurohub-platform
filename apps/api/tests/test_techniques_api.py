"""Phase 2 — Technique Module API endpoint tests."""

import json
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.technique import TechniqueModule

pytestmark = pytest.mark.anyio

VALID_PAYLOAD = {
    "key": "TEST_FDG_PET",
    "title_ko": "FDG PET 분석",
    "title_en": "FDG PET Analysis",
    "modality": "PET",
    "category": "Metabolic Imaging",
    "description": "FDG-PET metabolic analysis",
    "docker_image": "neurohub/fdg-pet:1.0.0",
    "version": "1.0.0",
    "qc_config": {"motion_threshold": 3.0},
    "output_schema": {"fields": ["suvr_map"]},
    "resource_requirements": {"gpu": True},
}


async def test_create_technique_returns_201(client: AsyncClient):
    resp = await client.post("/api/v1/admin/techniques", json=VALID_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["key"] == "TEST_FDG_PET"
    assert data["modality"] == "PET"
    assert data["status"] == "ACTIVE"
    assert data["qc_config"]["motion_threshold"] == 3.0


async def test_create_duplicate_key_returns_409(client: AsyncClient):
    payload = {**VALID_PAYLOAD, "key": "DUP_KEY_409"}
    resp1 = await client.post("/api/v1/admin/techniques", json=payload)
    assert resp1.status_code == 201
    resp2 = await client.post("/api/v1/admin/techniques", json=payload)
    assert resp2.status_code == 409


async def test_list_techniques_excludes_deprecated(client: AsyncClient, db: AsyncSession):
    # Create active + deprecated
    active = {**VALID_PAYLOAD, "key": "LIST_ACTIVE"}
    await client.post("/api/v1/admin/techniques", json=active)

    dep = {**VALID_PAYLOAD, "key": "LIST_DEPRECATED"}
    resp = await client.post("/api/v1/admin/techniques", json=dep)
    dep_id = resp.json()["id"]
    await client.delete(f"/api/v1/admin/techniques/{dep_id}")

    resp = await client.get("/api/v1/techniques")
    assert resp.status_code == 200
    keys = [t["key"] for t in resp.json()["items"]]
    assert "LIST_ACTIVE" in keys
    assert "LIST_DEPRECATED" not in keys


async def test_get_technique_by_id(client: AsyncClient):
    payload = {**VALID_PAYLOAD, "key": "GET_BY_ID"}
    resp = await client.post("/api/v1/admin/techniques", json=payload)
    tid = resp.json()["id"]

    resp = await client.get(f"/api/v1/techniques/{tid}")
    assert resp.status_code == 200
    assert resp.json()["key"] == "GET_BY_ID"


async def test_update_technique(client: AsyncClient):
    payload = {**VALID_PAYLOAD, "key": "UPDATE_TEST"}
    resp = await client.post("/api/v1/admin/techniques", json=payload)
    tid = resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/admin/techniques/{tid}",
        json={"docker_image": "neurohub/fdg-pet:2.0.0"},
    )
    assert resp.status_code == 200
    assert resp.json()["docker_image"] == "neurohub/fdg-pet:2.0.0"


async def test_deprecate_technique(client: AsyncClient, db: AsyncSession):
    payload = {**VALID_PAYLOAD, "key": "DEPRECATE_TEST"}
    resp = await client.post("/api/v1/admin/techniques", json=payload)
    tid = resp.json()["id"]

    resp = await client.delete(f"/api/v1/admin/techniques/{tid}")
    assert resp.status_code == 204

    row = (await db.execute(
        select(TechniqueModule).where(TechniqueModule.id == uuid.UUID(tid))
    )).scalar_one()
    assert row.status == "DEPRECATED"


async def test_non_admin_cannot_create(client_as, service_user):
    async with client_as(service_user) as c:
        resp = await c.post("/api/v1/admin/techniques", json=VALID_PAYLOAD)
        assert resp.status_code == 403


async def test_list_techniques_returns_all_18_after_seed(client: AsyncClient, db: AsyncSession):
    """Seed 18 techniques via the seed function and verify list returns all."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from scripts.seed_techniques import seed_techniques

    await seed_techniques(db)

    resp = await client.get("/api/v1/techniques")
    assert resp.status_code == 200
    data = resp.json()
    # May have extras from other tests, but must have all 18 standard ones
    keys = {t["key"] for t in data["items"]}
    expected = {
        "FDG_PET", "Amyloid_PET", "Tau_PET", "Cortical_Thickness", "VBM",
        "Diffusion_Properties", "Tractography", "EEG_Spectrum", "EEG_Connectivity",
        "EEG_MEM", "EEG_DCM", "MEG_Source", "MEG_Connectivity", "MEG_DCM",
        "fMRI_Task", "fMRI_Connectivity", "fMRI_DCM", "fMRI_MEM",
    }
    assert expected.issubset(keys), f"Missing: {expected - keys}"
