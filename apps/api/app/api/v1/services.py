import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.dependencies import AuthenticatedUser, CurrentUser, DbSession, require_roles
from app.models.service import PipelineDefinition, ServiceDefinition
from app.schemas.service import (
    PipelineListResponse,
    PipelineRead,
    ServiceCreate,
    ServiceListResponse,
    ServiceRead,
    ServiceUpdate,
)

router = APIRouter(tags=["Services"])


def _service_to_read(s: ServiceDefinition) -> ServiceRead:
    return ServiceRead(
        id=s.id,
        institution_id=s.institution_id,
        name=s.name,
        display_name=s.display_name,
        description=s.description,
        version=s.version,
        version_label=s.version_label,
        status=s.status,
        department=s.department,
        category=s.category,
        input_schema=s.input_schema,
        upload_slots=s.upload_slots,
        options_schema=s.options_schema,
        pricing=s.pricing,
        output_schema=s.output_schema,
        created_at=s.created_at,
    )


@router.get("/services", response_model=ServiceListResponse)
async def list_services(
    db: DbSession,
    user: AuthenticatedUser,
    status: str | None = None,
):
    q = select(ServiceDefinition).where(ServiceDefinition.institution_id == user.institution_id)
    if status:
        q = q.where(ServiceDefinition.status == status)
    q = q.order_by(ServiceDefinition.display_name.asc(), ServiceDefinition.version.desc()).limit(
        200
    )

    result = await db.execute(q)
    services = result.scalars().all()
    return ServiceListResponse(items=[_service_to_read(s) for s in services])


@router.get("/services/{service_id}", response_model=ServiceRead)
async def get_service(
    service_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return _service_to_read(service)


@router.get("/services/{service_id}/pipelines", response_model=PipelineListResponse)
async def list_pipelines(
    service_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
):
    service_result = await db.execute(
        select(ServiceDefinition.id).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    if not service_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Service not found")

    pipeline_result = await db.execute(
        select(PipelineDefinition)
        .where(PipelineDefinition.service_id == service_id)
        .order_by(PipelineDefinition.is_default.desc(), PipelineDefinition.created_at.desc())
        .limit(200)
    )
    pipelines = pipeline_result.scalars().all()

    return PipelineListResponse(
        items=[
            PipelineRead(
                id=p.id,
                service_id=p.service_id,
                name=p.name,
                version=p.version,
                is_default=p.is_default,
                created_at=p.created_at,
            )
            for p in pipelines
        ]
    )


# ---------------------------------------------------------------------------
# Admin Service CRUD
# ---------------------------------------------------------------------------


@router.post("/admin/services", response_model=ServiceRead, status_code=201)
async def create_service(
    body: ServiceCreate,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """Register a new service with full JSON definition."""
    defn = body.definition
    service = ServiceDefinition(
        institution_id=user.institution_id,
        name=body.name,
        display_name=body.display_name,
        description=body.description,
        version=1,
        version_label="1.0.0",
        department=body.department,
        category=body.category,
        status="DRAFT",
        created_by=user.id,
        input_schema=defn.input_schema.model_dump() if defn and defn.input_schema else None,
        upload_slots=(
            [s.model_dump() for s in defn.upload_slots] if defn and defn.upload_slots else None
        ),
        options_schema=(defn.options_schema.model_dump() if defn and defn.options_schema else None),
        pricing=defn.pricing.model_dump() if defn and defn.pricing else None,
        output_schema=(defn.output_schema.model_dump() if defn and defn.output_schema else None),
    )
    db.add(service)
    await db.flush()
    await db.refresh(service)
    return _service_to_read(service)


@router.patch("/admin/services/{service_id}", response_model=ServiceRead)
async def update_service(
    service_id: uuid.UUID,
    body: ServiceUpdate,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    if service.is_immutable:
        raise HTTPException(status_code=409, detail="Service version is immutable")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(service, key, value)

    await db.flush()
    await db.refresh(service)
    return _service_to_read(service)


@router.patch("/admin/services/{service_id}/publish", response_model=ServiceRead)
async def publish_service(
    service_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """DRAFT → PUBLISHED. Marks as immutable."""
    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    if service.status != "DRAFT":
        raise HTTPException(status_code=409, detail=f"Cannot publish from status {service.status}")

    service.status = "PUBLISHED"
    service.is_immutable = True
    await db.flush()
    await db.refresh(service)
    return _service_to_read(service)


@router.patch("/admin/services/{service_id}/deprecate", response_model=ServiceRead)
async def deprecate_service(
    service_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """PUBLISHED → DEPRECATED."""
    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    if service.status != "PUBLISHED":
        raise HTTPException(
            status_code=409, detail=f"Cannot deprecate from status {service.status}"
        )

    service.status = "DEPRECATED"
    await db.flush()
    await db.refresh(service)
    return _service_to_read(service)


@router.post(
    "/admin/services/{service_id}/new-version", response_model=ServiceRead, status_code=201
)
async def create_new_version(
    service_id: uuid.UUID,
    body: ServiceCreate,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """Create a new version of a published service. Old version stays immutable."""
    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    parent = result.scalar_one_or_none()
    if not parent:
        raise HTTPException(status_code=404, detail="Service not found")

    defn = body.definition
    new_version = parent.version + 1
    service = ServiceDefinition(
        institution_id=user.institution_id,
        name=parent.name,
        display_name=body.display_name or parent.display_name,
        description=body.description or parent.description,
        version=new_version,
        version_label=f"{new_version}.0.0",
        department=body.department or parent.department,
        category=body.category or parent.category,
        status="DRAFT",
        created_by=user.id,
        parent_service_id=parent.id,
        input_schema=defn.input_schema.model_dump()
        if defn and defn.input_schema
        else parent.input_schema,
        upload_slots=(
            [s.model_dump() for s in defn.upload_slots]
            if defn and defn.upload_slots
            else parent.upload_slots
        ),
        options_schema=(
            defn.options_schema.model_dump()
            if defn and defn.options_schema
            else parent.options_schema
        ),
        pricing=defn.pricing.model_dump() if defn and defn.pricing else parent.pricing,
        output_schema=(
            defn.output_schema.model_dump() if defn and defn.output_schema else parent.output_schema
        ),
    )
    db.add(service)
    await db.flush()
    await db.refresh(service)
    return _service_to_read(service)
