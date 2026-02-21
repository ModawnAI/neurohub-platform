import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.dependencies import AuthenticatedUser, DbSession
from app.models.institution import Institution, InstitutionMember
from app.models.user import User
from app.schemas.auth import MeResponse, OnboardingRequest, ProfileUpdate

router = APIRouter(prefix="/auth", tags=["Auth"])

USER_TYPE_TO_ROLE = {
    "SERVICE_USER": "PHYSICIAN",
    "EXPERT": "REVIEWER",
    "ADMIN": "SYSTEM_ADMIN",
}


@router.post("/onboarding", response_model=MeResponse, status_code=status.HTTP_201_CREATED)
async def complete_onboarding(body: OnboardingRequest, db: DbSession, user: AuthenticatedUser):
    existing = await db.execute(select(User).where(User.id == user.id))
    db_user = existing.scalar_one_or_none()

    if db_user and db_user.onboarding_completed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Onboarding already completed")

    if not db_user:
        db_user = User(
            id=user.id,
            username=user.username,
            email=user.username if "@" in user.username else None,
            supabase_user_id=user.id,
        )
        db.add(db_user)

    db_user.display_name = body.display_name
    db_user.user_type = body.user_type
    db_user.phone = body.phone
    db_user.onboarding_completed = True

    if body.user_type == "EXPERT":
        db_user.specialization = body.specialization
        db_user.bio = body.bio
        db_user.expert_status = "PENDING_APPROVAL"

    role_scope = USER_TYPE_TO_ROLE.get(body.user_type, "PHYSICIAN")

    org_type = (body.organization_type or "individual").upper()
    if org_type == "INDIVIDUAL" or not body.organization_name:
        org_code = f"personal-{str(user.id)[:8]}"
        org_name = f"{body.display_name}님의 개인 계정"
        org_type_value = "INDIVIDUAL"
    else:
        org_code = body.organization_code or f"org-{uuid.uuid4().hex[:8]}"
        org_name = body.organization_name
        org_type_value = org_type if org_type in ("HOSPITAL", "CLINIC") else "HOSPITAL"

    existing_org = await db.execute(select(Institution).where(Institution.code == org_code))
    institution = existing_org.scalar_one_or_none()

    if not institution:
        institution = Institution(
            code=org_code,
            name=org_name,
            status="ACTIVE",
            institution_type=org_type_value,
            created_by=user.id,
        )
        db.add(institution)
        await db.flush()

    existing_member = await db.execute(
        select(InstitutionMember).where(
            InstitutionMember.institution_id == institution.id,
            InstitutionMember.user_id == user.id,
        )
    )
    if not existing_member.scalar_one_or_none():
        db.add(InstitutionMember(
            institution_id=institution.id,
            user_id=user.id,
            role_scope=role_scope,
        ))

    await db.flush()
    await db.refresh(db_user)

    return MeResponse(
        id=db_user.id,
        username=db_user.username,
        display_name=db_user.display_name,
        email=db_user.email,
        phone=db_user.phone,
        user_type=db_user.user_type,
        institution_id=institution.id,
        institution_name=institution.name,
        roles=[role_scope],
        expert_status=db_user.expert_status,
        specialization=db_user.specialization,
        bio=db_user.bio,
        onboarding_completed=db_user.onboarding_completed,
        created_at=db_user.created_at,
    )


@router.get("/me", response_model=MeResponse)
async def get_me(db: DbSession, user: AuthenticatedUser):
    result = await db.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one_or_none()

    if not db_user:
        return MeResponse(
            id=user.id,
            username=user.username,
            roles=user.roles,
            onboarding_completed=False,
        )

    member_result = await db.execute(
        select(InstitutionMember, Institution)
        .join(Institution, InstitutionMember.institution_id == Institution.id)
        .where(InstitutionMember.user_id == user.id)
    )
    membership = member_result.first()

    institution_id = membership[0].institution_id if membership else None
    institution_name = membership[1].name if membership else None
    role_scope = membership[0].role_scope if membership else None
    roles = [role_scope] if role_scope else user.roles

    return MeResponse(
        id=db_user.id,
        username=db_user.username,
        display_name=db_user.display_name,
        email=db_user.email,
        phone=db_user.phone,
        user_type=db_user.user_type,
        institution_id=institution_id,
        institution_name=institution_name,
        roles=roles,
        expert_status=db_user.expert_status,
        specialization=db_user.specialization,
        bio=db_user.bio,
        onboarding_completed=db_user.onboarding_completed,
        created_at=db_user.created_at,
    )


@router.patch("/me", response_model=MeResponse)
async def update_profile(body: ProfileUpdate, db: DbSession, user: AuthenticatedUser):
    result = await db.execute(select(User).where(User.id == user.id))
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
        .join(Institution, InstitutionMember.institution_id == Institution.id)
        .where(InstitutionMember.user_id == user.id)
    )
    membership = member_result.first()

    return MeResponse(
        id=db_user.id,
        username=db_user.username,
        display_name=db_user.display_name,
        email=db_user.email,
        phone=db_user.phone,
        user_type=db_user.user_type,
        institution_id=membership[0].institution_id if membership else None,
        institution_name=membership[1].name if membership else None,
        roles=[membership[0].role_scope] if membership and membership[0].role_scope else user.roles,
        expert_status=db_user.expert_status,
        specialization=db_user.specialization,
        bio=db_user.bio,
        onboarding_completed=db_user.onboarding_completed,
        created_at=db_user.created_at,
    )
