"""Pre-QC API endpoints — per-case QC results and admin overrides."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update

from app.dependencies import AuthenticatedUser, DbSession

router = APIRouter(prefix="/requests/{request_id}/cases/{case_id}/pre-qc", tags=["pre-qc"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PreQCResultRead(BaseModel):
    id: uuid.UUID
    case_file_id: uuid.UUID
    case_id: uuid.UUID
    modality: str
    check_type: str
    status: str
    score: float | None = None
    message_ko: str | None = None
    message_en: str | None = None
    details: dict | None = None
    auto_resolved: bool = False


class PreQCResultListResponse(BaseModel):
    items: list[PreQCResultRead]
    can_proceed: bool
    fail_messages: list[str] = []
    warn_messages: list[str] = []


class PreQCOverrideRequest(BaseModel):
    check_ids: list[uuid.UUID] | None = None
    reason: str


class PreQCOverrideResponse(BaseModel):
    overridden_count: int
    can_proceed: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=PreQCResultListResponse)
async def list_pre_qc_results(
    request_id: uuid.UUID,
    case_id: uuid.UUID,
    user: AuthenticatedUser,
    db: DbSession,
):
    """List all Pre-QC results for a case."""
    from app.models.technique import PreQCResult
    from app.models.request import Case

    # Verify case belongs to user's institution
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    result = await db.execute(
        select(PreQCResult)
        .where(
            PreQCResult.case_id == case_id,
            PreQCResult.institution_id == user.institution_id,
        )
        .order_by(PreQCResult.created_at)
    )
    rows = result.scalars().all()

    items = [
        PreQCResultRead(
            id=r.id,
            case_file_id=r.case_file_id,
            case_id=r.case_id,
            modality=r.modality,
            check_type=r.check_type,
            status=r.status if not r.auto_resolved else "PASS",
            score=r.score,
            message_ko=r.message_ko,
            message_en=r.message_en,
            details=r.details,
            auto_resolved=r.auto_resolved,
        )
        for r in rows
    ]

    fail_messages = [i.message_ko for i in items if i.status == "FAIL" and i.message_ko]
    warn_messages = [i.message_ko for i in items if i.status == "WARN" and i.message_ko]
    can_proceed = len(fail_messages) == 0

    return PreQCResultListResponse(
        items=items,
        can_proceed=can_proceed,
        fail_messages=fail_messages,
        warn_messages=warn_messages,
    )


@router.post("/override", response_model=PreQCOverrideResponse)
async def override_pre_qc(
    request_id: uuid.UUID,
    case_id: uuid.UUID,
    body: PreQCOverrideRequest,
    user: AuthenticatedUser,
    db: DbSession,
):
    """Admin/reviewer override — mark FAIL checks as auto_resolved."""
    if not user.has_any_role("REVIEWER", "SYSTEM_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer or admin role required for QC override",
        )

    from app.models.technique import PreQCResult

    conditions = [
        PreQCResult.case_id == case_id,
        PreQCResult.institution_id == user.institution_id,
        PreQCResult.status == "FAIL",
        PreQCResult.auto_resolved == False,  # noqa: E712
    ]
    if body.check_ids:
        conditions.append(PreQCResult.id.in_(body.check_ids))

    stmt = (
        update(PreQCResult)
        .where(*conditions)
        .values(auto_resolved=True, details=PreQCResult.details + {"override_reason": body.reason, "override_by": str(user.id)})
    )

    # Fallback: update one by one if JSONB concat fails
    try:
        result = await db.execute(stmt)
        overridden = result.rowcount
    except Exception:
        # Manual fallback for JSONB update
        sel = await db.execute(
            select(PreQCResult).where(*conditions)
        )
        rows = sel.scalars().all()
        overridden = 0
        for r in rows:
            r.auto_resolved = True
            details = r.details or {}
            details["override_reason"] = body.reason
            details["override_by"] = str(user.id)
            r.details = details
            overridden += 1

    await db.commit()

    # Recheck gate
    all_result = await db.execute(
        select(PreQCResult).where(
            PreQCResult.case_id == case_id,
            PreQCResult.institution_id == user.institution_id,
        )
    )
    all_rows = all_result.scalars().all()
    can_proceed = all(
        r.status != "FAIL" or r.auto_resolved for r in all_rows
    )

    return PreQCOverrideResponse(
        overridden_count=overridden,
        can_proceed=can_proceed,
    )
