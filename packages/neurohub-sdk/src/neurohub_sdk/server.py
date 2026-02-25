"""HTTP server that wraps a BaseService into a standardized container.

Endpoints:
    GET  /health       — Liveness check
    GET  /health/ready — Readiness check
    GET  /schema       — Returns service schema definition
    POST /predict      — Accepts JobSpec, returns structured output
"""

from __future__ import annotations

import logging
import time
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from neurohub_sdk.base import BaseService
from neurohub_sdk.context import InputContext

logger = logging.getLogger("neurohub_sdk.server")


def create_app(service: BaseService) -> FastAPI:
    """Create a FastAPI app wrapping the given service."""

    app = FastAPI(
        title=f"NeuroHub Service: {service.config.display_name}",
        version=service.config.version,
    )

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "service": service.config.name,
            "version": service.config.version,
        }

    @app.get("/health/ready")
    async def ready():
        return {"status": "ready"}

    @app.get("/schema")
    async def schema():
        return {
            "name": service.config.name,
            "version": service.config.version,
            "display_name": service.config.display_name,
            "description": service.config.description,
            "department": service.config.department,
            "schema": service.schema.to_dict(),
        }

    @app.post("/predict")
    async def predict(request: Request):
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=422, content={"error": "Invalid JSON"})

        start_time = time.monotonic()

        try:
            ctx = InputContext.from_job_spec(body)
        except Exception as e:
            return JSONResponse(
                status_code=200,
                content={
                    "run_id": body.get("run_id", ""),
                    "status": "FAILED",
                    "results": {},
                    "files": {},
                    "metrics": {},
                    "error": {
                        "message": f"Failed to parse input: {e}",
                        "code": "INPUT_PARSE_ERROR",
                    },
                },
            )

        try:
            output = await service.predict(ctx)
        except KeyError as e:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return JSONResponse(
                status_code=200,
                content={
                    "run_id": body.get("run_id", ""),
                    "status": "FAILED",
                    "results": {},
                    "files": {},
                    "metrics": {"processing_time_ms": elapsed_ms},
                    "error": {
                        "message": str(e),
                        "code": "MISSING_INPUT",
                    },
                },
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.exception("Service predict failed: %s", e)
            return JSONResponse(
                status_code=200,
                content={
                    "run_id": body.get("run_id", ""),
                    "status": "FAILED",
                    "results": {},
                    "files": {},
                    "metrics": {"processing_time_ms": elapsed_ms},
                    "error": {
                        "message": str(e),
                        "code": "SERVICE_ERROR",
                    },
                },
            )

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        result = output.to_dict()
        result["metrics"]["processing_time_ms"] = elapsed_ms
        return JSONResponse(status_code=200, content=result)

    return app
