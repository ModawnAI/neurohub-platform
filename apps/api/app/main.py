import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.api.internal.routes import router as internal_router
from app.api.v1.router import api_v1_router
from app.config import settings
from app.database import engine
from app.exceptions import NeuroHubError, RateLimitError
from app.metrics import MetricsMiddleware, metrics_endpoint
from app.middleware.logging import RequestLoggingMiddleware, setup_logging
from app.middleware.rate_limit import RateLimitMiddleware

logger = logging.getLogger("neurohub")


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(api_v1_router)
app.include_router(internal_router)

# Metrics endpoint (excluded from OpenAPI schema)
app.get("/metrics", include_in_schema=False)(metrics_endpoint)


def _request_id(request: Request) -> str:
    """Extract or generate a request ID for structured logging."""
    return request.headers.get("x-request-id", str(uuid.uuid4())[:8])


@app.exception_handler(NeuroHubError)
async def neurohub_error_handler(request: Request, exc: NeuroHubError):
    rid = _request_id(request)
    log_level = logging.WARNING if exc.status_code < 500 else logging.ERROR
    logger.log(
        log_level,
        "[%s] %s %s → %d %s: %s",
        rid,
        request.method,
        request.url.path,
        exc.status_code,
        exc.code,
        exc.message,
    )
    headers = {}
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.detail.get("retry_after", 60))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "detail": exc.detail,
            "request_id": rid,
        },
        headers=headers,
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    rid = _request_id(request)
    # Map common HTTP status codes to structured error codes
    code_map = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        429: "RATE_LIMITED",
    }
    error_code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    logger.warning(
        "[%s] %s %s → %d %s",
        rid,
        request.method,
        request.url.path,
        exc.status_code,
        message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_code,
            "message": message,
            "detail": detail,
            "request_id": rid,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    rid = _request_id(request)
    logger.warning(
        "[%s] %s %s → 422 validation error (%d issues)",
        rid,
        request.method,
        request.url.path,
        len(exc.errors()),
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "detail": {"errors": exc.errors()},
            "request_id": rid,
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    rid = _request_id(request)
    logger.exception(
        "[%s] %s %s → 500 unhandled %s: %s",
        rid,
        request.method,
        request.url.path,
        type(exc).__name__,
        exc,
    )
    # Never leak internal details in production
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "detail": {},
            "request_id": rid,
        },
    )


@app.get("/", include_in_schema=False)
async def root():
    return {"name": settings.app_name, "version": settings.app_version, "health": "/api/v1/health"}
