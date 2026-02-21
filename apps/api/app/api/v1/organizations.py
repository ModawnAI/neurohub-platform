import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.dependencies import AuthenticatedUser, DbSession, require_roles
from app.models.institution import Institution, InstitutionInvite, InstitutionMember
from app.models.user import User
from app.schemas.organization import (
    InviteCreate,
    InviteRead,
    JoinRequest,
    MemberRead,
    OrgCreate,
    OrgListResponse,
    OrgRead,
    OrgUpdate,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


async def _org_to_read(db, institution: Institution) -> OrgRead:
    count_result = await db.execute(
        select(func.count(InstitutionMember.user_id)).where(
            InstitutionMember.institution_id == institution.id
        )
    )
    member_count = count_result.scalar() or 0

    return OrgRead(
        id=institution.id,
        code=institution.code,
        name=institution.name,
        status=institution.status,
        institution_type=institution.institution_type,
        contact_email=institution.contact_email,
        contact_phone=institution.contact_phone,
        member_count=member_count,
        created_at=institution.created_at,
    )


@router.post("", response_model=OrgRead, status_code=status.HTTP_201_CREATED)
async def create_organization(body: OrgCreate, db: DbSession, user: AuthenticatedUser):
    existing = await db.execute(select(Institution).where(Institution.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization code already exists")

    institution = Institution(
        code=body.code,
        name=body.name,
        status="ACTIVE",
        institution_type=body.institution_type,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        created_by=user.id,
    )
    db.add(institution)
    await db.flush()

    db.add(InstitutionMember(
        institution_id=institution.id,
        user_id=user.id,
        role_scope="SYSTEM_ADMIN",
    ))
    await db.flush()
    await db.refresh(institution)

    return await _org_to_read(db, institution)


@router.get("", response_model=OrgListResponse)
async def list_organizations(db: DbSession, user: AuthenticatedUser):
    if user.has_any_role("SYSTEM_ADMIN"):
        query = select(Institution).order_by(Institution.created_at.desc())
    else:
        query = (
            select(Institution)
            .join(InstitutionMember, InstitutionMember.institution_id == Institution.id)
            .where(InstitutionMember.user_id == user.id)
            .order_by(Institution.created_at.desc())
        )

    result = await db.execute(query)
    institutions = result.scalars().all()

    items = []
    for inst in institutions:
        items.append(await _org_to_read(db, inst))

    return OrgListResponse(items=items, total=len(items))


@router.patch("/{org_id}", response_model=OrgRead)
async def update_organization(org_id: str, body: OrgUpdate, db: DbSession, user: AuthenticatedUser):
    result = await db.execute(select(Institution).where(Institution.id == org_id))
    institution = result.scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    member_result = await db.execute(
        select(InstitutionMember).where(
            InstitutionMember.institution_id == institution.id,
            InstitutionMember.user_id == user.id,
        )
    )
    membership = member_result.scalar_one_or_none()
    if not membership and not user.has_any_role("SYSTEM_ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(institution, field, value)

    await db.flush()
    await db.refresh(institution)
    return await _org_to_read(db, institution)


@router.get("/{org_id}/members", response_model=list[MemberRead])
async def list_members(org_id: str, db: DbSession, user: AuthenticatedUser):
    result = await db.execute(
        select(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .where(InstitutionMember.institution_id == org_id)
        .order_by(InstitutionMember.created_at.desc())
    )
    rows = result.all()

    return [
        MemberRead(
            user_id=row[0].user_id,
            username=row[1].username,
            display_name=row[1].display_name,
            email=row[1].email,
            role_scope=row[0].role_scope,
            user_type=row[1].user_type,
            created_at=row[0].created_at,
        )
        for row in rows
    ]


@router.post("/{org_id}/invite", response_model=InviteRead, status_code=status.HTTP_201_CREATED)
async def create_invite(org_id: str, body: InviteCreate, db: DbSession, user: AuthenticatedUser):
    result = await db.execute(select(Institution).where(Institution.id == org_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    invite = InstitutionInvite(
        institution_id=org_id,
        email=body.email,
        role_scope=body.role_scope,
        invite_token=secrets.token_urlsafe(32),
        status="PENDING",
        invited_by=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)
    await db.flush()
    await db.refresh(invite)

    return InviteRead(
        id=invite.id,
        email=invite.email,
        role_scope=invite.role_scope,
        status=invite.status,
        invite_token=invite.invite_token,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@router.post("/join", status_code=status.HTTP_200_OK)
async def join_organization(body: JoinRequest, db: DbSession, user: AuthenticatedUser):
    result = await db.execute(
        select(InstitutionInvite).where(InstitutionInvite.invite_token == body.invite_token)
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite token")
    if invite.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invite already used or expired")
    if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite expired")

    existing_member = await db.execute(
        select(InstitutionMember).where(
            InstitutionMember.institution_id == invite.institution_id,
            InstitutionMember.user_id == user.id,
        )
    )
    if existing_member.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member")

    db.add(InstitutionMember(
        institution_id=invite.institution_id,
        user_id=user.id,
        role_scope=invite.role_scope or "PHYSICIAN",
    ))
    invite.status = "ACCEPTED"

    await db.flush()
    return {"status": "joined", "institution_id": str(invite.institution_id)}


@router.delete("/{org_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(org_id: str, member_user_id: str, db: DbSession, user: AuthenticatedUser):
    result = await db.execute(
        select(InstitutionMember).where(
            InstitutionMember.institution_id == org_id,
            InstitutionMember.user_id == member_user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if str(member_user_id) != str(user.id) and not user.has_any_role("SYSTEM_ADMIN"):
        caller_result = await db.execute(
            select(InstitutionMember).where(
                InstitutionMember.institution_id == org_id,
                InstitutionMember.user_id == user.id,
            )
        )
        caller_member = caller_result.scalar_one_or_none()
        if not caller_member or caller_member.role_scope != "SYSTEM_ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    await db.delete(membership)
    await db.flush()
