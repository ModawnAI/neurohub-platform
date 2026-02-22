import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Simple in-memory sliding window rate limiter.
# For production, replace with Redis-backed sliding window.

_WINDOW_SEC = 60
_LIMIT_UNAUTH = 60
_LIMIT_AUTH = 300

# ip -> list of timestamps
_buckets: dict[str, list[float]] = {}


def _cleanup(bucket: list[float], now: float) -> list[float]:
    cutoff = now - _WINDOW_SEC
    return [t for t in bucket if t > cutoff]


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip health checks
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        has_auth = bool(
            request.headers.get("authorization") or request.headers.get("x-api-key")
        )
        limit = _LIMIT_AUTH if has_auth else _LIMIT_UNAUTH

        now = time.time()
        bucket = _cleanup(_buckets.get(client_ip, []), now)

        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={"error": "RATE_LIMITED", "message": "Too many requests"},
                headers={"Retry-After": str(_WINDOW_SEC)},
            )

        bucket.append(now)
        _buckets[client_ip] = bucket

        return await call_next(request)
