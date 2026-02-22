import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.security.supabase_jwt import verify_supabase_jwt


class CurrentUser(BaseModel):
    id: uuid.UUID
    username: str
    institution_id: uuid.UUID
    roles: list[str] = []
    user_type: str | None = None
    api_key_scopes: list[str] | None = None

    def has_any_role(self, *roles: str) -> bool:
        role_set = set(self.roles)
        return any(role in role_set for role in roles)

    def has_scope(self, scope: str) -> bool:
        """Check if the user (via API key) has a required scope.

        Returns True if the user is not an API key user (no scope restrictions)
        or if the scope is in the user's API key scopes.
        """
        if self.api_key_scopes is None:
            return True
        return scope in self.api_key_scopes


def require_roles(*roles: str):
    async def checker(user: CurrentUser = Depends(get_current_user)):
        if not user.has_any_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(sorted(roles))}",
            )
        return user
    return checker


def _parse_uuid_or_default(value: str | None, default: str) -> uuid.UUID:
    try:
        return uuid.UUID(value) if value else uuid.UUID(default)
    except ValueError:
        return uuid.UUID(default)


def _parse_roles(value: object) -> list[str]:
    if value is None:
        return []

    raw_roles: list[str]
    if isinstance(value, str):
        raw_roles = [r.strip() for r in value.split(",") if r.strip()]
    elif isinstance(value, list):
        raw_roles = [str(v).strip() for v in value if str(v).strip()]
    else:
        raw_roles = [str(value).strip()] if str(value).strip() else []

    return sorted({r.upper() for r in raw_roles})


def _extract_claim_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _user_from_jwt_claims(claims: dict) -> CurrentUser:
    app_meta = _extract_claim_dict(claims.get("app_metadata"))
    user_meta = _extract_claim_dict(claims.get("user_metadata"))

    institution_claim = (
        claims.get("institution_id")
        or app_meta.get("institution_id")
        or user_meta.get("institution_id")
        or settings.default_institution_id
    )
    user_id = _parse_uuid_or_default(str(claims.get("sub")), "00000000-0000-0000-0000-000000000000")
    institution_id = _parse_uuid_or_default(str(institution_claim), settings.default_institution_id)

    roles = (
        _parse_roles(claims.get("roles"))
        or _parse_roles(app_meta.get("roles"))
        or _parse_roles(claims.get("role"))
    )
    if not roles:
        roles = ["PHYSICIAN"]

    username = (
        str(claims.get("preferred_username") or "").strip()
        or str(claims.get("email") or "").strip()
        or str(claims.get("phone") or "").strip()
        or str(user_id)
    )

    return CurrentUser(
        id=user_id,
        username=username,
        institution_id=institution_id,
        roles=roles,
    )


async def _resolve_api_key(api_key: str, db: AsyncSession) -> CurrentUser | None:
    """Resolve an API key to a CurrentUser. Returns None if key is invalid."""
    from app.models.institution import InstitutionApiKey

    prefix = api_key[:12]
    result = await db.execute(
        select(InstitutionApiKey).where(
            InstitutionApiKey.key_prefix == prefix,
            InstitutionApiKey.status == "ACTIVE",
        )
    )
    key_record = result.scalar_one_or_none()
    if not key_record:
        return None

    # Constant-time comparison
    expected_hash = key_record.key_hash
    actual_hash = hashlib.sha256(api_key.encode()).hexdigest()
    if not hmac.compare_digest(expected_hash, actual_hash):
        return None

    # Check expiration
    if key_record.expires_at and key_record.expires_at < datetime.now(timezone.utc):
        return None

    # Update last_used_at
    key_record.last_used_at = datetime.now(timezone.utc)

    return CurrentUser(
        id=key_record.created_by or uuid.UUID("00000000-0000-0000-0000-000000000000"),
        username=f"api-key:{key_record.name}",
        institution_id=key_record.institution_id,
        roles=["PHYSICIAN"],
        user_type="SERVICE_USER",
        api_key_scopes=key_record.scopes or ["read", "write"],
    )


async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_username: str | None = Header(default=None),
    x_institution_id: str | None = Header(default=None),
    x_roles: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    # 1. API Key authentication (B2B)
    if x_api_key:
        user = await _resolve_api_key(x_api_key, db)
        if user:
            return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
        )

    # 2. JWT Bearer token authentication
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            claims = await verify_supabase_jwt(token)
            return _user_from_jwt_claims(claims)

    if not (settings.allow_dev_auth_fallback and (settings.app_debug or settings.app_env == "development")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required",
        )

    # Development bootstrap resolver for local testing.
    user_id = _parse_uuid_or_default(
        x_user_id,
        "00000000-0000-0000-0000-000000000000",
    )
    institution_id = _parse_uuid_or_default(
        x_institution_id,
        settings.default_institution_id,
    )
    roles = [r.strip() for r in (x_roles or "SYSTEM_ADMIN").split(",") if r.strip()]
    return CurrentUser(
        id=user_id,
        username=x_username or "dev-user",
        institution_id=institution_id,
        roles=[r.upper() for r in roles],
    )


DbSession = Annotated[AsyncSession, Depends(get_db)]
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
