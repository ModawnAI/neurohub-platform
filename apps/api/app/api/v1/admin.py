from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.dependencies import AuthenticatedUser, DbSession, require_roles
from app.models.institution import Institution
from app.models.request import Request
from app.models.service import ServiceDefinition
from app.models.user import User
from app.schemas.request import RequestListResponse, RequestRead

router = APIRouter(prefix="/admin", tags=["Admin"])

AdminUser = Depends(require_roles("SYSTEM_ADMIN"))


def _to_read(req: Request) -> RequestRead:
    return RequestRead(
        id=req.id,
        institution_id=req.institution_id,
        service_id=req.service_id,
        pipeline_id=req.pipeline_id,
        status=req.status,
        priority=req.priority,
        inputs=req.inputs,
        options=req.options,
        requested_by=req.requested_by,
        department=req.department,
        error_detail=req.error_detail,
        cancel_reason=req.cancel_reason,
        idempotency_key=req.idempotency_key,
        service_snapshot=req.service_snapshot,
        pipeline_snapshot=req.pipeline_snapshot,
        case_count=len(req.cases) if req.cases else 0,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


@router.get("/stats")
async def get_admin_stats(db: DbSession, user: AuthenticatedUser = AdminUser):
    total_requests = (await db.execute(select(func.count(Request.id)))).scalar() or 0

    status_counts = {}
    status_result = await db.execute(
        select(Request.status, func.count(Request.id)).group_by(Request.status)
    )
    for row in status_result.all():
        status_counts[row[0]] = row[1]

    active_users = (await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )).scalar() or 0

    pending_experts = (await db.execute(
        select(func.count(User.id)).where(
            User.user_type == "EXPERT",
            User.expert_status == "PENDING_APPROVAL",
        )
    )).scalar() or 0

    approved_experts = (await db.execute(
        select(func.count(User.id)).where(
            User.user_type == "EXPERT",
            User.expert_status == "APPROVED",
        )
    )).scalar() or 0

    total_services = (await db.execute(
        select(func.count(ServiceDefinition.id)).where(ServiceDefinition.status == "ACTIVE")
    )).scalar() or 0

    total_organizations = (await db.execute(
        select(func.count(Institution.id)).where(Institution.status == "ACTIVE")
    )).scalar() or 0

    return {
        "total_requests": total_requests,
        "status_counts": status_counts,
        "active_users": active_users,
        "pending_experts": pending_experts,
        "approved_experts": approved_experts,
        "total_services": total_services,
        "total_organizations": total_organizations,
    }


@router.get("/requests", response_model=RequestListResponse)
async def list_all_requests(
    db: DbSession,
    user: AuthenticatedUser = AdminUser,
    request_status: str | None = Query(default=None, alias="status"),
):
    query = select(Request).options(selectinload(Request.cases))

    if request_status:
        query = query.where(Request.status == request_status)

    query = query.order_by(Request.created_at.desc())
    result = await db.execute(query)
    requests = result.scalars().all()

    count_query = select(func.count(Request.id))
    if request_status:
        count_query = count_query.where(Request.status == request_status)
    total = (await db.execute(count_query)).scalar() or 0

    return RequestListResponse(
        items=[_to_read(r) for r in requests],
        total=total,
    )
