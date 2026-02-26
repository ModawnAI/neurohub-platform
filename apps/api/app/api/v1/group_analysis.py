import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.dependencies import AuthenticatedUser, DbSession
from app.models.group_analysis import GroupStudy, GroupStudyMember
from app.schemas.group_analysis import (
    AddMemberRequest,
    GroupStudyBrief,
    GroupStudyCreate,
    GroupStudyRead,
)
from app.services.group_analysis_service import run_group_analysis

router = APIRouter(prefix="/group-studies", tags=["Group Analysis"])


async def _get_study_or_404(
    db: DbSession,
    study_id: uuid.UUID,
    institution_id: uuid.UUID,
) -> GroupStudy:
    result = await db.execute(
        select(GroupStudy).where(
            GroupStudy.id == study_id,
            GroupStudy.institution_id == institution_id,
        )
    )
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study not found")
    return study


@router.post("", response_model=GroupStudyRead, status_code=status.HTTP_201_CREATED)
async def create_group_study(
    body: GroupStudyCreate,
    user: AuthenticatedUser,
    db: DbSession,
) -> GroupStudy:
    study = GroupStudy(
        institution_id=user.institution_id,
        name=body.name,
        description=body.description,
        service_id=body.service_id,
        analysis_type=body.analysis_type,
        config=body.config,
        created_by=user.id,
        status="DRAFT",
    )
    db.add(study)
    await db.commit()
    await db.refresh(study)
    return study


@router.get("", response_model=list[GroupStudyBrief])
async def list_group_studies(
    user: AuthenticatedUser,
    db: DbSession,
) -> list[GroupStudyBrief]:
    result = await db.execute(
        select(GroupStudy).where(
            GroupStudy.institution_id == user.institution_id,
        ).order_by(GroupStudy.created_at.desc())
    )
    studies = list(result.scalars())
    return [
        GroupStudyBrief(
            id=s.id,
            name=s.name,
            description=s.description,
            service_id=s.service_id,
            status=s.status,
            analysis_type=s.analysis_type,
            member_count=len(s.members),
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in studies
    ]


@router.get("/{study_id}", response_model=GroupStudyRead)
async def get_group_study(
    study_id: uuid.UUID,
    user: AuthenticatedUser,
    db: DbSession,
) -> GroupStudy:
    return await _get_study_or_404(db, study_id, user.institution_id)


@router.post("/{study_id}/members", response_model=GroupStudyRead, status_code=status.HTTP_201_CREATED)
async def add_study_member(
    study_id: uuid.UUID,
    body: AddMemberRequest,
    user: AuthenticatedUser,
    db: DbSession,
) -> GroupStudy:
    study = await _get_study_or_404(db, study_id, user.institution_id)

    # Check duplicate
    existing_result = await db.execute(
        select(GroupStudyMember).where(
            GroupStudyMember.study_id == study_id,
            GroupStudyMember.request_id == body.request_id,
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Request is already a member of this study",
        )

    member = GroupStudyMember(
        study_id=study_id,
        request_id=body.request_id,
        group_label=body.group_label,
        member_metadata=body.member_metadata,
    )
    db.add(member)
    await db.commit()
    await db.refresh(study)
    return study


@router.delete("/{study_id}/members/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_study_member(
    study_id: uuid.UUID,
    request_id: uuid.UUID,
    user: AuthenticatedUser,
    db: DbSession,
) -> None:
    await _get_study_or_404(db, study_id, user.institution_id)

    result = await db.execute(
        select(GroupStudyMember).where(
            GroupStudyMember.study_id == study_id,
            GroupStudyMember.request_id == request_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    await db.delete(member)
    await db.commit()


@router.post("/{study_id}/run", response_model=GroupStudyRead)
async def trigger_group_analysis(
    study_id: uuid.UUID,
    user: AuthenticatedUser,
    db: DbSession,
) -> GroupStudy:
    study = await _get_study_or_404(db, study_id, user.institution_id)

    if len(study.members) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Need at least 2 members to run analysis",
        )

    if study.status == "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis is already running",
        )

    try:
        study = await run_group_analysis(study_id, db)
        await db.commit()
        await db.refresh(study)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {exc}",
        )

    return study


@router.get("/{study_id}/result")
async def get_study_result(
    study_id: uuid.UUID,
    user: AuthenticatedUser,
    db: DbSession,
) -> dict:
    study = await _get_study_or_404(db, study_id, user.institution_id)
    if study.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No result available (status: {study.status})",
        )
    return study.result or {}
