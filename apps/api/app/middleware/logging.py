"""Structured JSON logging middleware with request ID correlation."""

import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("neurohub.access")


class StructuredFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Add extra fields
        for key in (
            "method",
            "path",
            "status_code",
            "duration_ms",
            "request_id",
            "client_ip",
            "user_id",
            "institution_id",
        ):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
        if record.exc_info and record.exc_info[1]:
            log_data["exception"] = str(record.exc_info[1])
        return json.dumps(log_data)


def setup_logging():
    """Configure structured logging for the application."""
    from app.config import settings

    root_logger = logging.getLogger("neurohub")
    root_logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    if settings.app_env == "production":
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))

    if not root_logger.handlers:
        root_logger.addHandler(handler)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4())[:8])
        start_time = time.time()

        response = await call_next(request)

        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        # Extract user context from request state (set by auth dependency)
        user_id = getattr(request.state, "user_id", None)
        institution_id = getattr(request.state, "institution_id", None)

        # Skip logging health checks to reduce noise
        if not request.url.path.startswith("/api/v1/health"):
            logger.info(
                "%s %s %s %.0fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                extra={
                    "method": request.method,
                    "path": str(request.url.path),
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "request_id": request_id,
                    "client_ip": request.client.host if request.client else "unknown",
                    "user_id": str(user_id) if user_id else None,
                    "institution_id": str(institution_id) if institution_id else None,
                },
            )

        return response
