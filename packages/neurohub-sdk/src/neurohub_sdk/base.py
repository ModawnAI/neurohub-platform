"""Base service class that all NeuroHub services inherit from."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neurohub_sdk.config import ServiceConfig
    from neurohub_sdk.context import InputContext, OutputContext
    from neurohub_sdk.schema import SchemaDefinition


class BaseService(abc.ABC):
    """Abstract base class for NeuroHub AI services.

    Subclasses must define:
        config: ServiceConfig — service metadata
        schema: SchemaDefinition — input/output schema
        predict(ctx) — the inference method
    """

    config: ServiceConfig
    schema: SchemaDefinition

    @abc.abstractmethod
    async def predict(self, ctx: "InputContext") -> "OutputContext":
        """Run inference on the given input context.

        Args:
            ctx: InputContext with access to inputs, files, demographics, options.

        Returns:
            OutputContext with results, files, and metrics.
        """
        ...

    def serve(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """Start the HTTP server for this service."""
        import uvicorn

        from neurohub_sdk.server import create_app

        app = create_app(self)
        uvicorn.run(app, host=host, port=port)
