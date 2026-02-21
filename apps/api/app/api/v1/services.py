import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.dependencies import AuthenticatedUser, DbSession
from app.models.service import PipelineDefinition, ServiceDefinition
from app.schemas.service import PipelineListResponse, PipelineRead, ServiceListResponse, ServiceRead

router = APIRouter(tags=["Services"])


@router.get("/services", response_model=ServiceListResponse)
async def list_services(
    db: DbSession,
    user: AuthenticatedUser,
):
    result = await db.execute(
        select(ServiceDefinition)
        .where(ServiceDefinition.institution_id == user.institution_id)
        .order_by(ServiceDefinition.display_name.asc(), ServiceDefinition.version.desc())
        .limit(200)
    )
    services = result.scalars().all()
    return ServiceListResponse(
        items=[
            ServiceRead(
                id=s.id,
                institution_id=s.institution_id,
                name=s.name,
                display_name=s.display_name,
                version=s.version,
                status=s.status,
                department=s.department,
                created_at=s.created_at,
            )
            for s in services
        ]
    )


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
    service = service_result.scalar_one_or_none()
    if not service:
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
