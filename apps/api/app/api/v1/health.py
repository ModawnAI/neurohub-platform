"""Health check endpoints: basic, liveness, and readiness probes."""

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.dependencies import DbSession
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc),
    )


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
