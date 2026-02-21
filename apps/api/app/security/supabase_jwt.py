from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.config import settings

_jwks_cache: dict[str, Any] | None = None
_jwks_cache_expires_at: float = 0.0
_jwks_lock = asyncio.Lock()


def _extract_max_age(cache_control: str | None) -> int | None:
    if not cache_control:
        return None
    parts = [part.strip() for part in cache_control.split(",")]
    for part in parts:
        if part.startswith("max-age="):
            value = part.split("=", 1)[1]
            if value.isdigit():
                return int(value)
    return None


async def _fetch_jwks() -> tuple[dict[str, Any], int]:
    timeout = httpx.Timeout(connect=3.0, read=5.0, write=5.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(settings.supabase_jwks_url)
        response.raise_for_status()
        payload = response.json()

    if not isinstance(payload, dict) or "keys" not in payload:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Invalid JWKS payload",
        )

    max_age = _extract_max_age(response.headers.get("cache-control"))
    ttl = max_age if max_age is not None else settings.supabase_jwks_cache_ttl_seconds
    return payload, max(ttl, 30)


async def get_jwks(force_refresh: bool = False) -> dict[str, Any]:
    global _jwks_cache, _jwks_cache_expires_at

    now = time.time()
    if not force_refresh and _jwks_cache and now < _jwks_cache_expires_at:
        return _jwks_cache

    async with _jwks_lock:
        now = time.time()
        if not force_refresh and _jwks_cache and now < _jwks_cache_expires_at:
            return _jwks_cache

        try:
            payload, ttl = await _fetch_jwks()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to fetch Supabase JWKS",
            ) from exc

        _jwks_cache = payload
        _jwks_cache_expires_at = now + ttl
        return payload


def _get_key_by_kid(jwks: dict[str, Any], kid: str | None) -> dict[str, Any] | None:
    keys = jwks.get("keys") if isinstance(jwks, dict) else None
    if not isinstance(keys, list):
        return None

    for key in keys:
        if isinstance(key, dict) and key.get("kid") == kid:
            return key
    return None


async def verify_supabase_jwt(token: str) -> dict[str, Any]:
    if not settings.supabase_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase JWKS is not configured",
        )

    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
        ) from exc

    kid = header.get("kid")
    jwks = await get_jwks(force_refresh=False)
    key = _get_key_by_kid(jwks, kid)
    if not key:
        jwks = await get_jwks(force_refresh=True)
        key = _get_key_by_kid(jwks, kid)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown token key id",
        )

    issuer = settings.supabase_issuer.strip() or ""
    if not issuer and settings.supabase_url:
        issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"

    audience = settings.supabase_jwt_audience.strip()
    options = {
        "verify_aud": bool(audience),
        "verify_iss": bool(issuer),
        "leeway": settings.supabase_jwt_clock_skew_seconds,
    }

    try:
        decode_kwargs: dict[str, Any] = {
            "token": token,
            "key": key,
            "algorithms": ["RS256", "ES256"],
            "options": options,
        }
        if audience:
            decode_kwargs["audience"] = audience
        if issuer:
            decode_kwargs["issuer"] = issuer

        claims = jwt.decode(**decode_kwargs)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed",
        ) from exc

    if not isinstance(claims, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )
    return claims
