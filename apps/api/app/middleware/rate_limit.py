"""Rate limiting middleware with Redis backend (falls back to in-memory)."""
import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("neurohub.rate_limit")

_WINDOW_SEC = 60
_LIMIT_UNAUTH = 60
_LIMIT_AUTH = 300

# In-memory fallback
_buckets: dict[str, list[float]] = {}


def _cleanup(bucket: list[float], now: float) -> list[float]:
    cutoff = now - _WINDOW_SEC
    return [t for t in bucket if t > cutoff]


class _InMemoryLimiter:
    def check_and_increment(self, key: str, limit: int) -> tuple[bool, int]:
        now = time.time()
        bucket = _cleanup(_buckets.get(key, []), now)
        if len(bucket) >= limit:
            return False, len(bucket)
        bucket.append(now)
        _buckets[key] = bucket
        return True, len(bucket)


class _RedisLimiter:
    def __init__(self, redis_client):
        self._redis = redis_client

    def check_and_increment(self, key: str, limit: int) -> tuple[bool, int]:
        try:
            pipe = self._redis.pipeline()
            now = time.time()
            window_key = f"rl:{key}"
            pipe.zremrangebyscore(window_key, 0, now - _WINDOW_SEC)
            pipe.zadd(window_key, {str(now): now})
            pipe.zcard(window_key)
            pipe.expire(window_key, _WINDOW_SEC + 1)
            results = pipe.execute()
            count = results[2]
            if count > limit:
                return False, count
            return True, count
        except Exception:
            logger.warning("Redis rate limiter failed, falling back to in-memory")
            return _InMemoryLimiter().check_and_increment(key, limit)


_limiter = None


def _get_rate_limiter():
    global _limiter
    if _limiter is not None:
        return _limiter
    try:
        import redis
        from app.config import settings
        client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        _limiter = _RedisLimiter(client)
        logger.info("Using Redis-backed rate limiter")
    except Exception:
        _limiter = _InMemoryLimiter()
        logger.info("Using in-memory rate limiter (Redis unavailable)")
    return _limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        from app.config import settings
        # Skip rate limiting in test/development and for health/metrics
        if settings.app_env in ("test", "development"):
            return await call_next(request)
        if request.url.path.startswith("/api/v1/health") or request.url.path == "/metrics":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        has_auth = bool(
            request.headers.get("authorization") or request.headers.get("x-api-key")
        )
        limit = _LIMIT_AUTH if has_auth else _LIMIT_UNAUTH

        limiter = _get_rate_limiter()
        allowed, count = limiter.check_and_increment(client_ip, limit)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "RATE_LIMITED", "message": "Too many requests"},
                headers={"Retry-After": str(_WINDOW_SEC)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response
