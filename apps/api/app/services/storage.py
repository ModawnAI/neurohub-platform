"""Supabase Storage service for presigned URL generation."""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

logger = logging.getLogger("neurohub.storage")

_STORAGE_BASE = f"{settings.supabase_url}/storage/v1" if settings.supabase_url else ""


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }


async def create_presigned_upload(
    bucket: str,
    path: str,
    *,
    expires_in: int = 900,
) -> str:
    """Generate a presigned upload URL via Supabase Storage REST API.

    Returns the presigned URL string.
    """
    url = f"{_STORAGE_BASE}/object/upload/sign/{bucket}/{path}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            url,
            headers=_headers(),
            json={"expiresIn": expires_in},
        )
        resp.raise_for_status()
        data = resp.json()
        # Supabase returns a relative signed URL — make it absolute
        signed_url = data.get("signedURL") or data.get("url", "")
        if signed_url.startswith("/"):
            signed_url = f"{settings.supabase_url}/storage/v1{signed_url}"
        return signed_url


async def create_presigned_download(
    bucket: str,
    path: str,
    *,
    expires_in: int = 900,
) -> str:
    """Generate a presigned download URL via Supabase Storage REST API."""
    url = f"{_STORAGE_BASE}/object/sign/{bucket}/{path}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            url,
            headers=_headers(),
            json={"expiresIn": expires_in},
        )
        resp.raise_for_status()
        data = resp.json()
        signed_url = data.get("signedURL") or data.get("url", "")
        if signed_url.startswith("/"):
            signed_url = f"{settings.supabase_url}/storage/v1{signed_url}"
        return signed_url
