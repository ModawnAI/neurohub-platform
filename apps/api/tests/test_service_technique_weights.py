"""Phase 3 — ServiceTechniqueWeight API tests."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.technique import ServiceTechniqueWeight, TechniqueModule
from tests.conftest import DEFAULT_SERVICE_ID

pytestmark = pytest.mark.anyio

# Helpers


async def _create_technique(db: AsyncSession, key: str) -> TechniqueModule:
    tm = TechniqueModule(
        key=key,
        title_ko=f"{key} 분석",
        title_en=f"{key} Analysis",
        modality="MRI",
        category="Structural",
        docker_image=f"neurohub/{key.lower()}:1.0.0",
    )
    db.add(tm)
    await db.flush()
    return tm


# Tests


async def test_add_technique_weight(client: AsyncClient, db: AsyncSession):
    tech = await _create_technique(db, "WEIGHT_ADD_T1")
    resp = await client.post(
        f"/api/v1/admin/services/{DEFAULT_SERVICE_ID}/techniques",
        json={"technique_module_id": str(tech.id), "base_weight": 0.35},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["base_weight"] == 0.35
    assert data["technique_key"] == "WEIGHT_ADD_T1"


async def test_list_weights_for_service(client: AsyncClient, db: AsyncSession):
    tech1 = await _create_technique(db, "LIST_W1")
    tech2 = await _create_technique(db, "LIST_W2")
    await client.post(
        f"/api/v1/admin/services/{DEFAULT_SERVICE_ID}/techniques",
        json={"technique_module_id": str(tech1.id), "base_weight": 0.5},
    )
    await client.post(
        f"/api/v1/admin/services/{DEFAULT_SERVICE_ID}/techniques",
        json={"technique_module_id": str(tech2.id), "base_weight": 0.5},
    )

    resp = await client.get(f"/api/v1/admin/services/{DEFAULT_SERVICE_ID}/techniques")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2


async def test_bulk_set_replaces_all(client: AsyncClient, db: AsyncSession):
    tech1 = await _create_technique(db, "BULK_A")
    tech2 = await _create_technique(db, "BULK_B")
    tech3 = await _create_technique(db, "BULK_C")

    # Add initial
    await client.post(
        f"/api/v1/admin/services/{DEFAULT_SERVICE_ID}/techniques",
        json={"technique_module_id": str(tech1.id), "base_weight": 1.0},
    )

    # Bulk replace with 2 different ones
    resp = await client.put(
        f"/api/v1/admin/services/{DEFAULT_SERVICE_ID}/techniques",
        json=[
            {"technique_module_id": str(tech2.id), "base_weight": 0.6},
            {"technique_module_id": str(tech3.id), "base_weight": 0.4},
        ],
    )
    assert resp.status_code == 200
    keys = {item["technique_key"] for item in resp.json()["items"]}
    assert keys == {"BULK_B", "BULK_C"}
    assert resp.json()["total"] == 2


async def test_weight_validation_rejects_gt_1(client: AsyncClient, db: AsyncSession):
    tech = await _create_technique(db, "WEIGHT_GT1")
    resp = await client.post(
        f"/api/v1/admin/services/{DEFAULT_SERVICE_ID}/techniques",
        json={"technique_module_id": str(tech.id), "base_weight": 1.5},
    )
    assert resp.status_code == 422


async def test_duplicate_technique_on_service_409(client: AsyncClient, db: AsyncSession):
    tech = await _create_technique(db, "DUP_WEIGHT")
    resp1 = await client.post(
        f"/api/v1/admin/services/{DEFAULT_SERVICE_ID}/techniques",
        json={"technique_module_id": str(tech.id), "base_weight": 0.5},
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        f"/api/v1/admin/services/{DEFAULT_SERVICE_ID}/techniques",
        json={"technique_module_id": str(tech.id), "base_weight": 0.3},
    )
    assert resp2.status_code == 409


async def test_remove_technique_weight(client: AsyncClient, db: AsyncSession):
    tech = await _create_technique(db, "REMOVE_W")
    await client.post(
        f"/api/v1/admin/services/{DEFAULT_SERVICE_ID}/techniques",
        json={"technique_module_id": str(tech.id), "base_weight": 0.5},
    )

    resp = await client.delete(
        f"/api/v1/admin/services/{DEFAULT_SERVICE_ID}/techniques/{tech.id}"
    )
    assert resp.status_code == 204


async def test_weights_isolated_per_service(client: AsyncClient, db: AsyncSession):
    """Weights on service A don't appear on service B."""
    from app.models.institution import Institution
    from app.models.service import ServiceDefinition
    from tests.conftest import DEFAULT_INSTITUTION_ID

    svc_b = ServiceDefinition(
        institution_id=DEFAULT_INSTITUTION_ID,
        name="svc-b",
        display_name="Service B",
        status="ACTIVE",
    )
    db.add(svc_b)
    await db.flush()

    tech = await _create_technique(db, "ISOLATION_T")
    await client.post(
        f"/api/v1/admin/services/{DEFAULT_SERVICE_ID}/techniques",
        json={"technique_module_id": str(tech.id), "base_weight": 0.8},
    )

    resp = await client.get(f"/api/v1/admin/services/{svc_b.id}/techniques")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_nonexistent_service_404(client: AsyncClient):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/admin/services/{fake_id}/techniques")
    assert resp.status_code == 404
