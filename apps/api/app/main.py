from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.internal.routes import router as internal_router
from app.api.v1.router import api_v1_router
from app.config import settings
from app.database import engine
from app.exceptions import NeuroHubError
from app.metrics import MetricsMiddleware, metrics_endpoint
from app.middleware.logging import RequestLoggingMiddleware, setup_logging
from app.middleware.rate_limit import RateLimitMiddleware


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


@app.exception_handler(NeuroHubError)
async def neurohub_error_handler(request, exc: NeuroHubError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "detail": {"errors": exc.errors()},
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request, exc: Exception):
    import logging
    logging.getLogger("neurohub").exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "detail": {},
        },
    )


@app.get("/", include_in_schema=False)
async def root():
    return {"name": settings.app_name, "version": settings.app_version, "health": "/api/v1/health"}
