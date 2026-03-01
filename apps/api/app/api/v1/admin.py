import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import String, func, select
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.audit import AuditLog
from app.models.institution import Institution
from app.models.request import Request
from app.models.service import ServiceDefinition
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.request import RequestRead

router = APIRouter(prefix="/admin", tags=["Admin"])

_require_admin = require_roles("SYSTEM_ADMIN")


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
async def get_admin_stats(db: DbSession, user: CurrentUser = Depends(_require_admin)):
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


@router.get("/requests", response_model=PaginatedResponse[RequestRead])
async def list_all_requests(
    db: DbSession,
    user: CurrentUser = Depends(_require_admin),
    request_status: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    query = select(Request).options(selectinload(Request.cases))
    count_query = select(func.count(Request.id))

    if request_status:
        query = query.where(Request.status == request_status)
        count_query = count_query.where(Request.status == request_status)

    if search:
        search_filter = Request.id.cast(String).ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(Request.created_at.desc()).offset(offset).limit(limit)
    )
    requests = result.scalars().all()

    return PaginatedResponse(
        items=[_to_read(r) for r in requests],
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + limit) < total,
    )


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

class AuditLogRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    institution_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID
    before_state: dict | None = None
    after_state: dict | None = None
    ip_address: str | None = None
    created_at: datetime


@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogRead])
async def list_audit_logs(
    db: DbSession,
    user: CurrentUser = Depends(_require_admin),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if from_date:
        filters.append(AuditLog.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        filters.append(AuditLog.created_at <= datetime.combine(to_date, datetime.max.time()))

    count_result = await db.execute(select(func.count(AuditLog.id)).where(*filters))
    total = count_result.scalar_one()

    result = await db.execute(
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    logs = result.scalars().all()

    return PaginatedResponse(
        items=[
            AuditLogRead(
                id=log.id,
                user_id=log.user_id,
                institution_id=log.institution_id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                before_state=log.before_state,
                after_state=log.after_state,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + limit) < total,
    )
