from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbSession, require_roles
from app.models.institution import Institution, InstitutionMember
from app.models.user import User
from app.schemas.user import ExpertApproval, UserListResponse, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])

_require_admin = require_roles("SYSTEM_ADMIN")


def _user_to_read(user: User, institution_id=None, institution_name=None, role_scope=None) -> UserRead:
    return UserRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        phone=user.phone,
        user_type=user.user_type,
        is_active=user.is_active,
        institution_id=institution_id,
        institution_name=institution_name,
        role_scope=role_scope,
        expert_status=user.expert_status,
        specialization=user.specialization,
        onboarding_completed=user.onboarding_completed,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("", response_model=UserListResponse)
async def list_users(
    db: DbSession,
    user: CurrentUser = Depends(_require_admin),
    user_type: str | None = Query(default=None),
    expert_status: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    query = (
        select(User, InstitutionMember, Institution)
        .outerjoin(InstitutionMember, InstitutionMember.user_id == User.id)
        .outerjoin(Institution, Institution.id == InstitutionMember.institution_id)
    )

    if user_type:
        query = query.where(User.user_type == user_type)
    if expert_status:
        query = query.where(User.expert_status == expert_status)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    count_query = select(func.count(User.id))
    if user_type:
        count_query = count_query.where(User.user_type == user_type)
    if expert_status:
        count_query = count_query.where(User.expert_status == expert_status)
    if is_active is not None:
        count_query = count_query.where(User.is_active == is_active)
    total = (await db.execute(count_query)).scalar() or 0

    items = [
        _user_to_read(
            row[0],
            institution_id=row[1].institution_id if row[1] else None,
            institution_name=row[2].name if row[2] else None,
            role_scope=row[1].role_scope if row[1] else None,
        )
        for row in rows
    ]

    return UserListResponse(items=items, total=total)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: str, db: DbSession, user: CurrentUser = Depends(_require_admin)):
    result = await db.execute(
        select(User, InstitutionMember, Institution)
        .outerjoin(InstitutionMember, InstitutionMember.user_id == User.id)
        .outerjoin(Institution, Institution.id == InstitutionMember.institution_id)
        .where(User.id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return _user_to_read(
        row[0],
        institution_id=row[1].institution_id if row[1] else None,
        institution_name=row[2].name if row[2] else None,
        role_scope=row[1].role_scope if row[1] else None,
    )


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(user_id: str, body: UserUpdate, db: DbSession, user: CurrentUser = Depends(_require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)

    await db.flush()
    await db.refresh(db_user)

    member_result = await db.execute(
        select(InstitutionMember, Institution)
        .outerjoin(Institution, Institution.id == InstitutionMember.institution_id)
        .where(InstitutionMember.user_id == db_user.id)
    )
    membership = member_result.first()

    return _user_to_read(
        db_user,
        institution_id=membership[0].institution_id if membership else None,
        institution_name=membership[1].name if membership else None,
        role_scope=membership[0].role_scope if membership else None,
    )


@router.post("/{user_id}/approve-expert", response_model=UserRead)
async def approve_expert(user_id: str, db: DbSession, user: CurrentUser = Depends(_require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if db_user.user_type != "EXPERT":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="User is not an expert")
    if db_user.expert_status == "APPROVED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Expert already approved")

    db_user.expert_status = "APPROVED"
    db_user.expert_approved_at = datetime.now(timezone.utc)
    db_user.expert_approved_by = user.id

    await db.flush()
    await db.refresh(db_user)

    member_result = await db.execute(
        select(InstitutionMember, Institution)
        .outerjoin(Institution, Institution.id == InstitutionMember.institution_id)
        .where(InstitutionMember.user_id == db_user.id)
    )
    membership = member_result.first()

    return _user_to_read(
        db_user,
        institution_id=membership[0].institution_id if membership else None,
        institution_name=membership[1].name if membership else None,
        role_scope=membership[0].role_scope if membership else None,
    )


@router.post("/{user_id}/reject-expert", response_model=UserRead)
async def reject_expert(user_id: str, body: ExpertApproval, db: DbSession, user: CurrentUser = Depends(_require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if db_user.user_type != "EXPERT":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="User is not an expert")

    db_user.expert_status = "REJECTED"
    await db.flush()
    await db.refresh(db_user)

    member_result = await db.execute(
        select(InstitutionMember, Institution)
        .outerjoin(Institution, Institution.id == InstitutionMember.institution_id)
        .where(InstitutionMember.user_id == db_user.id)
    )
    membership = member_result.first()

    return _user_to_read(
        db_user,
        institution_id=membership[0].institution_id if membership else None,
        institution_name=membership[1].name if membership else None,
        role_scope=membership[0].role_scope if membership else None,
    )
