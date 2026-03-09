"""Health check endpoints: basic, liveness, and readiness probes."""

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.dependencies import DbSession

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health(db: DbSession):
    """Full health check — returns status of all backend services.

    This endpoint does NOT require authentication.
    """
    services: dict[str, str | dict] = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        services["database"] = "ok"
    except Exception as e:
        services["database"] = {"status": "error", "message": str(e)[:200]}

    # Redis check
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        services["redis"] = "ok"
    except Exception as e:
        services["redis"] = {"status": "error", "message": str(e)[:200]}

    # MinIO / S3-compatible storage check
    try:
        import asyncio

        import boto3
        from botocore.client import Config

        def _check_minio():
            client = boto3.client(
                "s3",
                endpoint_url=settings.minio_endpoint,
                aws_access_key_id=settings.minio_access_key,
                aws_secret_access_key=settings.minio_secret_key,
                config=Config(signature_version="s3v4"),
                region_name=settings.minio_region,
            )
            client.list_buckets()

        await asyncio.to_thread(_check_minio)
        services["storage"] = "ok"
    except Exception as e:
        services["storage"] = {"status": "error", "message": str(e)[:200]}

    all_ok = all(v == "ok" for v in services.values())
    status_label = "ok" if all_ok else "degraded"

    return {
        "status": status_label,
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
    }


@router.get("/health/live")
async def liveness():
    """Liveness probe — always returns 200 if the process is alive."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: DbSession):
    """Readiness probe — checks database (and optionally Redis) connectivity."""
    checks: dict[str, str] = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "fail"

    # Redis check
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "fail"

    all_ok = all(v == "ok" for v in checks.values())
    status_label = "ready" if all_ok else "degraded"
    status_code = 200 if all_ok else 503

    return JSONResponse(
        content={"status": status_label, "checks": checks},
        status_code=status_code,
    )
