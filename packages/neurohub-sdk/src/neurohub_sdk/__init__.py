"""NeuroHub Service SDK — standardized framework for building medical AI services.

Usage:
    from neurohub_sdk import BaseService, InputContext, OutputContext, ServiceConfig
    from neurohub_sdk.schema import SchemaDefinition, InputField, OutputField, UploadSlot

    class MyService(BaseService):
        config = ServiceConfig(name="my-service", version="1.0.0", display_name="My Service")
        schema = SchemaDefinition(
            inputs=[InputField(key="text", type="text", label="텍스트", required=True)],
            outputs=[OutputField(key="result", type="text", label="결과")],
        )

        async def predict(self, ctx: InputContext) -> OutputContext:
            text = ctx.get_input("text")
            output = ctx.create_output()
            output.set("result", text.upper())
            return output

    if __name__ == "__main__":
        MyService().serve()
"""

from neurohub_sdk.base import BaseService
from neurohub_sdk.context import InputContext, OutputContext
from neurohub_sdk.config import ServiceConfig

__all__ = [
    "BaseService",
    "InputContext",
    "OutputContext",
    "ServiceConfig",
]

__version__ = "0.1.0"
