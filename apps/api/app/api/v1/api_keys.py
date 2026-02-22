"""API key management endpoints for B2B access."""

import hashlib
import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.dependencies import AuthenticatedUser, CurrentUser, DbSession, require_roles
from app.models.institution import InstitutionApiKey

router = APIRouter(tags=["API Keys"])

API_KEY_PREFIX = "nhk_"


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    expires_at: datetime | None = None


class ApiKeyCreateResponse(BaseModel):
    id: uuid.UUID
    key: str  # full key, shown only once
    name: str
    key_prefix: str
    expires_at: datetime | None


class ApiKeyRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    key_prefix: str
    status: str
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


@router.post("/organizations/{org_id}/api-keys", response_model=ApiKeyCreateResponse)
async def create_api_key(
    org_id: uuid.UUID,
    body: ApiKeyCreate,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    # Verify the org belongs to the user's institution
    if org_id != user.institution_id:
        raise HTTPException(status_code=403, detail="Cannot create keys for other institutions")

    # Generate the key
    raw_key = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    prefix = raw_key[:12]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = InstitutionApiKey(
        institution_id=org_id,
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
        status="ACTIVE",
        expires_at=body.expires_at,
        created_by=user.id,
    )
    db.add(api_key)
    await db.flush()

    return ApiKeyCreateResponse(
        id=api_key.id,
        key=raw_key,
        name=api_key.name,
        key_prefix=prefix,
        expires_at=api_key.expires_at,
    )


@router.get("/organizations/{org_id}/api-keys", response_model=list[ApiKeyRead])
async def list_api_keys(
    org_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    if org_id != user.institution_id:
        raise HTTPException(status_code=403, detail="Cannot view keys for other institutions")

    result = await db.execute(
        select(InstitutionApiKey)
        .where(InstitutionApiKey.institution_id == org_id)
        .order_by(InstitutionApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        ApiKeyRead(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            status=k.status,
            last_used_at=k.last_used_at,
            expires_at=k.expires_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete("/organizations/{org_id}/api-keys/{key_id}")
async def revoke_api_key(
    org_id: uuid.UUID,
    key_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser = Depends(require_roles("SYSTEM_ADMIN")),
):
    if org_id != user.institution_id:
        raise HTTPException(status_code=403, detail="Cannot revoke keys for other institutions")

    result = await db.execute(
        select(InstitutionApiKey).where(
            InstitutionApiKey.id == key_id,
            InstitutionApiKey.institution_id == org_id,
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.status = "REVOKED"
    await db.flush()
    return {"status": "revoked"}
