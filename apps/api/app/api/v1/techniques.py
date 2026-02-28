"""Technique Module CRUD API + Execution endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select

from pydantic import BaseModel, Field

from app.config import settings
from app.dependencies import AuthenticatedUser, CurrentUser, DbSession, require_roles
from app.models.request import Request
from app.models.run import Run
from app.models.service import ServiceDefinition
from app.models.technique import ServiceTechniqueWeight, TechniqueModule, TechniqueRun
from app.schemas.technique import (
    TechniqueModuleCreate,
    TechniqueModuleListResponse,
    TechniqueModuleRead,
    TechniqueModuleUpdate,
)
from app.services.technique_orchestrator import on_technique_complete
from app.services.technique_output import TechniqueOutput, validate_technique_output


# --- Weight schemas (inline, small) ---

class WeightCreate(BaseModel):
    technique_module_id: uuid.UUID
    base_weight: float = Field(..., gt=0, le=1.0)
    is_required: bool = True
    override_qc_config: dict | None = None


class WeightRead(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    technique_module_id: uuid.UUID
    technique_key: str | None = None
    base_weight: float
    is_required: bool
    override_qc_config: dict | None


class WeightListResponse(BaseModel):
    items: list[WeightRead]
    total: int

router = APIRouter(tags=["Techniques"])


def _to_read(t: TechniqueModule) -> TechniqueModuleRead:
    return TechniqueModuleRead(
        id=t.id,
        key=t.key,
        title_ko=t.title_ko,
        title_en=t.title_en,
        modality=t.modality,
        category=t.category,
        description=t.description,
        docker_image=t.docker_image,
        version=t.version,
        status=t.status,
        qc_config=t.qc_config,
        output_schema=t.output_schema,
        resource_requirements=t.resource_requirements,
        created_at=t.created_at,
    )


# --- Public endpoints ---


@router.get("/techniques", response_model=TechniqueModuleListResponse)
async def list_techniques(
    db: DbSession,
    user: AuthenticatedUser,
    modality: str | None = None,
    category: str | None = None,
):
    q = select(TechniqueModule).where(TechniqueModule.status == "ACTIVE")
    if modality:
        q = q.where(TechniqueModule.modality == modality)
    if category:
        q = q.where(TechniqueModule.category == category)
    q = q.order_by(TechniqueModule.key)

    result = await db.execute(q)
    items = result.scalars().all()

    return TechniqueModuleListResponse(
        items=[_to_read(t) for t in items],
        total=len(items),
    )


@router.get("/techniques/{technique_id}", response_model=TechniqueModuleRead)
async def get_technique(
    technique_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    t = (await db.execute(
        select(TechniqueModule).where(TechniqueModule.id == technique_id)
    )).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Technique module not found")
    return _to_read(t)


# --- Admin endpoints ---


@router.post("/admin/techniques", response_model=TechniqueModuleRead, status_code=201)
async def create_technique(
    payload: TechniqueModuleCreate,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    existing = (await db.execute(
        select(TechniqueModule).where(TechniqueModule.key == payload.key)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Technique key '{payload.key}' already exists")

    t = TechniqueModule(**payload.model_dump())
    db.add(t)
    await db.flush()
    return _to_read(t)


@router.patch("/admin/techniques/{technique_id}", response_model=TechniqueModuleRead)
async def update_technique(
    technique_id: uuid.UUID,
    payload: TechniqueModuleUpdate,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    t = (await db.execute(
        select(TechniqueModule).where(TechniqueModule.id == technique_id)
    )).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Technique module not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(t, field, value)
    await db.flush()
    return _to_read(t)


@router.delete("/admin/techniques/{technique_id}", status_code=204)
async def deprecate_technique(
    technique_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    t = (await db.execute(
        select(TechniqueModule).where(TechniqueModule.id == technique_id)
    )).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Technique module not found")
    t.status = "DEPRECATED"
    await db.flush()


# --- Service-Technique Weight endpoints ---


def _weight_to_read(w: ServiceTechniqueWeight, technique_key: str | None = None) -> WeightRead:
    return WeightRead(
        id=w.id,
        service_id=w.service_id,
        technique_module_id=w.technique_module_id,
        technique_key=technique_key,
        base_weight=w.base_weight,
        is_required=w.is_required,
        override_qc_config=w.override_qc_config,
    )


async def _get_service_or_404(db, service_id: uuid.UUID) -> ServiceDefinition:
    svc = (await db.execute(
        select(ServiceDefinition).where(ServiceDefinition.id == service_id)
    )).scalar_one_or_none()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    return svc


@router.get("/admin/services/{service_id}/techniques", response_model=WeightListResponse)
async def list_service_techniques(
    service_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    await _get_service_or_404(db, service_id)
    q = (
        select(ServiceTechniqueWeight, TechniqueModule.key)
        .join(TechniqueModule, ServiceTechniqueWeight.technique_module_id == TechniqueModule.id)
        .where(ServiceTechniqueWeight.service_id == service_id)
        .order_by(ServiceTechniqueWeight.base_weight.desc())
    )
    rows = (await db.execute(q)).all()
    items = [_weight_to_read(w, key) for w, key in rows]
    return WeightListResponse(items=items, total=len(items))


@router.post("/admin/services/{service_id}/techniques", response_model=WeightRead, status_code=201)
async def add_technique_weight(
    service_id: uuid.UUID,
    payload: WeightCreate,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    await _get_service_or_404(db, service_id)

    # Check technique exists
    tech = (await db.execute(
        select(TechniqueModule).where(TechniqueModule.id == payload.technique_module_id)
    )).scalar_one_or_none()
    if not tech:
        raise HTTPException(status_code=404, detail="Technique module not found")

    # Check duplicate
    existing = (await db.execute(
        select(ServiceTechniqueWeight).where(
            ServiceTechniqueWeight.service_id == service_id,
            ServiceTechniqueWeight.technique_module_id == payload.technique_module_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Technique already linked to this service")

    w = ServiceTechniqueWeight(
        service_id=service_id,
        technique_module_id=payload.technique_module_id,
        base_weight=payload.base_weight,
        is_required=payload.is_required,
        override_qc_config=payload.override_qc_config,
    )
    db.add(w)
    await db.flush()
    return _weight_to_read(w, tech.key)


@router.put("/admin/services/{service_id}/techniques", response_model=WeightListResponse)
async def bulk_set_techniques(
    service_id: uuid.UUID,
    payload: list[WeightCreate],
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    await _get_service_or_404(db, service_id)

    # Delete existing
    existing = (await db.execute(
        select(ServiceTechniqueWeight).where(ServiceTechniqueWeight.service_id == service_id)
    )).scalars().all()
    for w in existing:
        await db.delete(w)
    await db.flush()

    # Insert new
    items = []
    for entry in payload:
        tech = (await db.execute(
            select(TechniqueModule).where(TechniqueModule.id == entry.technique_module_id)
        )).scalar_one_or_none()
        if not tech:
            raise HTTPException(status_code=404, detail=f"Technique {entry.technique_module_id} not found")

        w = ServiceTechniqueWeight(
            service_id=service_id,
            technique_module_id=entry.technique_module_id,
            base_weight=entry.base_weight,
            is_required=entry.is_required,
            override_qc_config=entry.override_qc_config,
        )
        db.add(w)
        await db.flush()
        items.append(_weight_to_read(w, tech.key))

    return WeightListResponse(items=items, total=len(items))


@router.delete("/admin/services/{service_id}/techniques/{technique_id}", status_code=204)
async def remove_technique_weight(
    service_id: uuid.UUID,
    technique_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    w = (await db.execute(
        select(ServiceTechniqueWeight).where(
            ServiceTechniqueWeight.service_id == service_id,
            ServiceTechniqueWeight.technique_module_id == technique_id,
        )
    )).scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Weight not found")
    await db.delete(w)
    await db.flush()


# --- Technique Run schemas ---


class TechniqueRunRead(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    technique_module_id: uuid.UUID
    technique_key: str
    status: str
    job_spec: dict | None = None
    output_data: dict | None = None
    qc_score: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_detail: str | None = None


class TechniqueRunListResponse(BaseModel):
    items: list[TechniqueRunRead]
    total: int


class TechniqueResultPayload(BaseModel):
    module: str
    module_version: str
    qc_score: float
    qc_flags: list[str]
    features: dict
    maps: dict
    confidence: float


def _tr_to_read(tr: TechniqueRun) -> TechniqueRunRead:
    return TechniqueRunRead(
        id=tr.id,
        run_id=tr.run_id,
        technique_module_id=tr.technique_module_id,
        technique_key=tr.technique_key,
        status=tr.status,
        job_spec=tr.job_spec,
        output_data=tr.output_data,
        qc_score=tr.qc_score,
        started_at=tr.started_at,
        completed_at=tr.completed_at,
        error_detail=tr.error_detail,
    )


# --- Technique Execution endpoints ---


async def _load_request_run_or_404(
    db: DbSession,
    request_id: uuid.UUID,
    run_id: uuid.UUID,
    institution_id: uuid.UUID,
) -> tuple[Request, Run]:
    """Load request + run, verifying institution ownership."""
    req = (await db.execute(
        select(Request).where(
            Request.id == request_id,
            Request.institution_id == institution_id,
        )
    )).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    run = (await db.execute(
        select(Run).where(Run.id == run_id, Run.request_id == request_id)
    )).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return req, run


@router.get(
    "/requests/{request_id}/runs/{run_id}/techniques",
    response_model=TechniqueRunListResponse,
)
async def list_technique_runs(
    request_id: uuid.UUID,
    run_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    """List all technique runs for a given run."""
    await _load_request_run_or_404(db, request_id, run_id, user.institution_id)

    result = await db.execute(
        select(TechniqueRun)
        .where(TechniqueRun.run_id == run_id)
        .order_by(TechniqueRun.created_at)
    )
    items = result.scalars().all()
    return TechniqueRunListResponse(
        items=[_tr_to_read(tr) for tr in items],
        total=len(items),
    )


@router.get(
    "/requests/{request_id}/runs/{run_id}/techniques/{technique_run_id}",
    response_model=TechniqueRunRead,
)
async def get_technique_run(
    request_id: uuid.UUID,
    run_id: uuid.UUID,
    technique_run_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Get a single technique run with output data."""
    await _load_request_run_or_404(db, request_id, run_id, user.institution_id)

    tr = (await db.execute(
        select(TechniqueRun).where(
            TechniqueRun.id == technique_run_id,
            TechniqueRun.run_id == run_id,
        )
    )).scalar_one_or_none()
    if not tr:
        raise HTTPException(status_code=404, detail="Technique run not found")

    return _tr_to_read(tr)


@router.get("/requests/{request_id}/runs/{run_id}/fusion")
async def get_fusion_result(
    request_id: uuid.UUID,
    run_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    """Get the fusion result for a run. Returns 404 if fusion hasn't been computed."""
    _, run = await _load_request_run_or_404(db, request_id, run_id, user.institution_id)

    if not run.output_data or "fusion" not in run.output_data:
        raise HTTPException(status_code=404, detail="Fusion result not available yet")

    return run.output_data["fusion"]


# --- Internal callback endpoint ---


@router.post("/internal/technique-runs/{technique_run_id}/result")
async def technique_run_callback(
    technique_run_id: uuid.UUID,
    payload: TechniqueResultPayload,
    db: DbSession,
    x_internal_key: str = Header(alias="X-Internal-Key"),
):
    """Internal callback: container reports technique result.

    Authenticated via X-Internal-Key header (shared secret).
    """
    expected_key = settings.internal_api_key or "test-internal-key"
    if x_internal_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid internal API key")

    output = TechniqueOutput(
        module=payload.module,
        module_version=payload.module_version,
        qc_score=payload.qc_score,
        qc_flags=payload.qc_flags,
        features=payload.features,
        maps=payload.maps,
        confidence=payload.confidence,
    )

    all_done = await on_technique_complete(db, technique_run_id, output)
    return {"technique_run_id": str(technique_run_id), "all_done": all_done}
