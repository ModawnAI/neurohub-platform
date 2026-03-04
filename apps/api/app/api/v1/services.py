import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.dependencies import AuthenticatedUser, CurrentUser, DbSession, require_roles
from app.models.evaluation import ServiceEvaluator
from app.models.service import PipelineDefinition, ServiceDefinition
from app.schemas.evaluation import (
    ServiceEvaluatorCreate,
    ServiceEvaluatorListResponse,
    ServiceEvaluatorRead,
)
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
        service_type=s.service_type,
        requires_evaluator=s.requires_evaluator,
        input_schema=s.input_schema,
        upload_slots=s.upload_slots,
        options_schema=s.options_schema,
        pricing=s.pricing,
        output_schema=s.output_schema,
        clinical_config=s.clinical_config,
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


class PipelineCreate(BaseModel):
    name: str
    version: str = "1.0.0"
    steps: list[dict] = []
    qc_rules: dict = {}
    is_default: bool = True


@router.post(
    "/admin/services/{service_id}/pipelines",
    response_model=PipelineRead,
    status_code=201,
)
async def create_pipeline(
    service_id: uuid.UUID,
    body: PipelineCreate,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """Create a pipeline for a service."""
    svc = await db.execute(
        select(ServiceDefinition.id).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    if not svc.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Service not found")

    pipeline = PipelineDefinition(
        service_id=service_id,
        name=body.name,
        version=body.version,
        steps=body.steps,
        qc_rules=body.qc_rules,
        is_default=body.is_default,
    )
    db.add(pipeline)
    await db.flush()
    await db.refresh(pipeline)

    return PipelineRead(
        id=pipeline.id,
        service_id=pipeline.service_id,
        name=pipeline.name,
        version=pipeline.version,
        is_default=pipeline.is_default,
        created_at=pipeline.created_at,
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
        service_type=body.service_type,
        requires_evaluator=body.requires_evaluator,
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


@router.delete("/admin/services/{service_id}", status_code=204)
async def delete_service(
    service_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """Permanently delete a service. Blocked if any requests reference it."""
    from app.models.request import Request

    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Check for existing requests
    from sqlalchemy import func

    req_count = (
        await db.execute(
            select(func.count()).where(Request.service_id == service_id)
        )
    ).scalar() or 0
    if req_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {req_count} request(s) reference this service",
        )

    # Delete related records first
    from app.models.technique import ServiceTechniqueWeight

    await db.execute(
        select(ServiceTechniqueWeight)
        .where(ServiceTechniqueWeight.service_id == service_id)
    )
    from sqlalchemy import delete as sa_delete

    await db.execute(
        sa_delete(ServiceTechniqueWeight).where(
            ServiceTechniqueWeight.service_id == service_id
        )
    )
    await db.execute(
        sa_delete(PipelineDefinition).where(
            PipelineDefinition.service_id == service_id
        )
    )
    await db.execute(
        sa_delete(ServiceEvaluator).where(
            ServiceEvaluator.service_id == service_id
        )
    )

    await db.delete(service)
    await db.flush()


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


# ---------------------------------------------------------------------------
# Evaluator Management
# ---------------------------------------------------------------------------


@router.get(
    "/admin/services/{service_id}/evaluators",
    response_model=ServiceEvaluatorListResponse,
)
async def list_evaluators(
    service_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    result = await db.execute(
        select(ServiceEvaluator).where(
            ServiceEvaluator.service_id == service_id,
            ServiceEvaluator.institution_id == user.institution_id,
            ServiceEvaluator.is_active.is_(True),
        )
    )
    evaluators = result.scalars().all()
    return ServiceEvaluatorListResponse(
        items=[
            ServiceEvaluatorRead(
                id=e.id,
                service_id=e.service_id,
                user_id=e.user_id,
                institution_id=e.institution_id,
                is_active=e.is_active,
                created_at=e.created_at,
            )
            for e in evaluators
        ]
    )


@router.post(
    "/admin/services/{service_id}/evaluators",
    response_model=ServiceEvaluatorRead,
    status_code=201,
)
async def assign_evaluator(
    service_id: uuid.UUID,
    body: ServiceEvaluatorCreate,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    svc = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    if not svc.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Service not found")

    existing = await db.execute(
        select(ServiceEvaluator).where(
            ServiceEvaluator.service_id == service_id,
            ServiceEvaluator.user_id == body.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Evaluator already assigned")

    evaluator = ServiceEvaluator(
        service_id=service_id,
        user_id=body.user_id,
        institution_id=user.institution_id,
        is_active=True,
    )
    db.add(evaluator)
    await db.flush()
    await db.refresh(evaluator)
    return ServiceEvaluatorRead(
        id=evaluator.id,
        service_id=evaluator.service_id,
        user_id=evaluator.user_id,
        institution_id=evaluator.institution_id,
        is_active=evaluator.is_active,
        created_at=evaluator.created_at,
    )


@router.delete(
    "/admin/services/{service_id}/evaluators/{user_id}",
    status_code=204,
)
async def remove_evaluator(
    service_id: uuid.UUID,
    user_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    result = await db.execute(
        select(ServiceEvaluator).where(
            ServiceEvaluator.service_id == service_id,
            ServiceEvaluator.user_id == user_id,
            ServiceEvaluator.institution_id == user.institution_id,
        )
    )
    evaluator = result.scalar_one_or_none()
    if not evaluator:
        raise HTTPException(status_code=404, detail="Evaluator assignment not found")

    evaluator.is_active = False
    await db.flush()


# ---------------------------------------------------------------------------
# Service Package Upload
# ---------------------------------------------------------------------------


class PackagePresignRequest(BaseModel):
    file_name: str
    content_type: str = "application/zip"
    file_size: int


class PackagePresignResponse(BaseModel):
    presigned_url: str
    storage_path: str
    expires_at: str


class PackageInfo(BaseModel):
    file_name: str
    file_size: int
    storage_path: str
    uploaded_at: str


@router.post(
    "/admin/services/{service_id}/package/presign",
    response_model=PackagePresignResponse,
)
async def presign_package_upload(
    service_id: uuid.UUID,
    body: PackagePresignRequest,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """Generate a presigned URL to upload a service package (zip/tar.gz/py)."""
    from app.config import settings
    from app.services import storage as storage_svc

    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Validate file type
    allowed_ext = (".zip", ".tar.gz", ".tgz", ".py", ".whl")
    if not any(body.file_name.lower().endswith(ext) for ext in allowed_ext):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_ext)}",
        )

    storage_path = (
        f"institutions/{user.institution_id}/services/{service_id}/"
        f"packages/{body.file_name}"
    )

    presigned_url = await storage_svc.create_presigned_upload(
        bucket=settings.storage_bucket_outputs,
        path=storage_path,
        expires_in=900,
    )

    from datetime import datetime, timedelta, timezone

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=900)

    return PackagePresignResponse(
        presigned_url=presigned_url,
        storage_path=storage_path,
        expires_at=expires_at.isoformat(),
    )


class PackageCompleteRequest(BaseModel):
    storage_path: str
    file_name: str
    file_size: int


@router.post(
    "/admin/services/{service_id}/package/complete",
    response_model=PackageInfo,
)
async def complete_package_upload(
    service_id: uuid.UUID,
    body: PackageCompleteRequest,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """Mark a package upload as complete. Stores the package path on the service."""
    data = body

    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    from datetime import datetime, timezone

    # Store package info in the service's output_schema (or a dedicated field)
    # We use a convention: service metadata stored in a special JSONB area
    package_info = {
        "file_name": data.file_name,
        "file_size": data.file_size,
        "storage_path": data.storage_path,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": str(user.id),
    }

    # Store in pricing JSONB as a temporary hack... better: use a dedicated column
    # Actually, let's just put it in a safe place: the service's existing JSONB
    # We'll use inputs_schema (legacy field) to store package metadata
    current_meta = service.inputs_schema or {}
    current_meta["_package"] = package_info
    service.inputs_schema = current_meta
    await db.flush()
    await db.refresh(service)

    return PackageInfo(
        file_name=data.file_name,
        file_size=data.file_size,
        storage_path=data.storage_path,
        uploaded_at=package_info["uploaded_at"],
    )


@router.get(
    "/admin/services/{service_id}/package",
    response_model=PackageInfo | None,
)
async def get_package_info(
    service_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """Get the current uploaded package info for a service."""
    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    meta = service.inputs_schema or {}
    pkg = meta.get("_package")
    if not pkg:
        return None

    return PackageInfo(
        file_name=pkg["file_name"],
        file_size=pkg["file_size"],
        storage_path=pkg["storage_path"],
        uploaded_at=pkg["uploaded_at"],
    )


@router.get("/admin/services/{service_id}/package/download")
async def download_package(
    service_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """Get a presigned download URL for the service package."""
    from app.config import settings
    from app.services import storage as storage_svc

    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    meta = service.inputs_schema or {}
    pkg = meta.get("_package")
    if not pkg:
        raise HTTPException(status_code=404, detail="No package uploaded")

    download_url = await storage_svc.create_presigned_download(
        bucket=settings.storage_bucket_outputs,
        path=pkg["storage_path"],
        expires_in=900,
    )

    return {"download_url": download_url, "filename": pkg["file_name"]}


# ---------------------------------------------------------------------------
# Service Container Deployment
# ---------------------------------------------------------------------------


class DeployServiceRequest(BaseModel):
    container_image: str | None = None  # If None, uses default registry tag
    resource_requirements: dict | None = None


class DeployServiceResponse(BaseModel):
    app_name: str
    image: str
    status: str
    machine_ids: list[str] | None = None


@router.post("/admin/services/{service_id}/deploy", response_model=DeployServiceResponse)
async def deploy_service(
    service_id: uuid.UUID,
    body: DeployServiceRequest,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """Deploy a service container to Fly.io."""
    from app.config import settings

    if not settings.fly_api_token:
        raise HTTPException(status_code=503, detail="Fly.io integration not configured")

    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    from app.services.service_deployer import ServiceDeployer

    deployer = ServiceDeployer(
        fly_api_token=settings.fly_api_token,
        fly_org=settings.fly_org,
        registry_host="registry.fly.io",
        api_base_url=settings.fly_machines_api_url,
    )

    service_def = {
        "id": str(service.id),
        "name": service.name,
        "display_name": service.display_name,
        "version": service.version,
        "version_label": service.version_label,
        "institution_id": str(service.institution_id),
        "container_image": body.container_image,
        "resource_requirements": body.resource_requirements or {},
    }

    # Create app (idempotent)
    await deployer.create_app(service_def)

    # Deploy
    record = await deployer.deploy(service_def)

    return DeployServiceResponse(
        app_name=record.app_name,
        image=record.image,
        status=record.status.value,
        machine_ids=record.machine_ids,
    )


class ServiceStatusResponse(BaseModel):
    app_name: str
    machines: list[dict]
    total: int


@router.get("/admin/services/{service_id}/deployment", response_model=ServiceStatusResponse)
async def get_deployment_status(
    service_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """Get deployment status for a service."""
    from app.config import settings

    if not settings.fly_api_token:
        raise HTTPException(status_code=503, detail="Fly.io integration not configured")

    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    from app.services.service_deployer import ServiceDeployer

    deployer = ServiceDeployer(
        fly_api_token=settings.fly_api_token,
        fly_org=settings.fly_org,
        api_base_url=settings.fly_machines_api_url,
    )

    app_name = f"neurohub-svc-{service.name.lower()}"
    try:
        machines = await deployer.list_machines(app_name)
    except Exception:
        machines = []

    return ServiceStatusResponse(
        app_name=app_name,
        machines=machines,
        total=len(machines),
    )


@router.delete("/admin/services/{service_id}/deployment", status_code=204)
async def undeploy_service(
    service_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    """Undeploy (stop all machines for) a service."""
    from app.config import settings

    if not settings.fly_api_token:
        raise HTTPException(status_code=503, detail="Fly.io integration not configured")

    result = await db.execute(
        select(ServiceDefinition).where(
            ServiceDefinition.id == service_id,
            ServiceDefinition.institution_id == user.institution_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    from app.services.service_deployer import ServiceDeployer

    deployer = ServiceDeployer(
        fly_api_token=settings.fly_api_token,
        fly_org=settings.fly_org,
        api_base_url=settings.fly_machines_api_url,
    )

    app_name = f"neurohub-svc-{service.name.lower()}"
    await deployer.undeploy(app_name)
