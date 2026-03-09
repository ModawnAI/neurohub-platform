import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.config import settings
from app.dependencies import AuthenticatedUser, DbSession
from app.models.institution import Institution, InstitutionMember
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    OnboardingRequest,
    ProfileUpdate,
    SignupRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

USER_TYPE_TO_ROLE = {
    "SERVICE_USER": "PHYSICIAN",
    "EXPERT": "REVIEWER",
    "ADMIN": "SYSTEM_ADMIN",
}


@router.post("/logout")
async def logout(user: AuthenticatedUser):
    """Log out the current user.

    For stateless JWT auth (local or Supabase), there is no server-side session
    to invalidate. The frontend should discard the token on its side.
    This endpoint exists so the frontend has a proper API to call.
    """
    return {"message": "로그아웃 되었습니다", "user_id": str(user.id)}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession):
    if not settings.use_local_auth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local auth disabled")

    from app.security.local_jwt import create_access_token, verify_password

    result = await db.execute(select(User).where(User.email == body.email))
    db_user = result.scalar_one_or_none()
    if not db_user or not db_user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="잘못된 이메일 또는 비밀번호입니다")
    if not verify_password(body.password, db_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="잘못된 이메일 또는 비밀번호입니다")

    db_user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    # Look up institution + role
    member_result = await db.execute(
        select(InstitutionMember).where(InstitutionMember.user_id == db_user.id)
    )
    membership = member_result.scalar_one_or_none()
    institution_id = str(membership.institution_id) if membership else settings.default_institution_id
    roles = [membership.role_scope] if membership and membership.role_scope else ["PHYSICIAN"]

    token = create_access_token(
        sub=str(db_user.id),
        email=db_user.email or "",
        roles=roles,
        institution_id=institution_id,
    )
    return TokenResponse(access_token=token)


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: DbSession):
    if not settings.use_local_auth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local auth disabled")

    from app.security.local_jwt import create_access_token, hash_password

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 등록된 이메일입니다")

    user_id = uuid.uuid4()
    display_name = body.name or body.email.split("@")[0]
    db_user = User(
        id=user_id,
        username=body.email,
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=display_name,
        user_type="SERVICE_USER",
        onboarding_completed=True,
    )
    db.add(db_user)
    await db.flush()

    # Auto-create personal institution + membership
    org_code = f"personal-{str(user_id)[:8]}"
    institution = Institution(
        code=org_code,
        name=f"{display_name}님의 개인 계정",
        status="ACTIVE",
        institution_type="INDIVIDUAL",
        created_by=user_id,
    )
    db.add(institution)
    await db.flush()

    db.add(InstitutionMember(
        institution_id=institution.id,
        user_id=user_id,
        role_scope="PHYSICIAN",
    ))
    await db.flush()

    token = create_access_token(
        sub=str(user_id),
        email=body.email,
        roles=["PHYSICIAN"],
        institution_id=str(institution.id),
    )
    return TokenResponse(access_token=token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(user: AuthenticatedUser, db: DbSession):
    if not settings.use_local_auth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local auth disabled")

    from app.security.local_jwt import create_access_token

    member_result = await db.execute(
        select(InstitutionMember).where(InstitutionMember.user_id == user.id)
    )
    membership = member_result.scalar_one_or_none()
    institution_id = str(membership.institution_id) if membership else str(user.institution_id)
    roles = [membership.role_scope] if membership and membership.role_scope else user.roles

    token = create_access_token(
        sub=str(user.id),
        email=user.username,
        roles=roles,
        institution_id=institution_id,
    )
    return TokenResponse(access_token=token)


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
