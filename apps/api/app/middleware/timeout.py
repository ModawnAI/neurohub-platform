import asyncio
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("neurohub")


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Return 504 if a request handler exceeds the timeout threshold."""

    def __init__(self, app, timeout: float = 30.0):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        # Skip timeout for health checks, metrics, and file uploads
        path = request.url.path
        if path.startswith("/api/v1/health") or path == "/metrics":
            return await call_next(request)

        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            logger.error(
                "Request timeout after %.1fs: %s %s",
                self.timeout,
                request.method,
                path,
            )
            return JSONResponse(
                status_code=504,
                content={
                    "error": "REQUEST_TIMEOUT",
                    "message": f"Request exceeded {self.timeout}s timeout",
                    "detail": {},
                },
            )
