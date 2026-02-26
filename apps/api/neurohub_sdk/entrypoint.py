"""Docker entrypoint: loads inference.py and calls run(ctx)."""
import importlib.util
import sys
import traceback
from neurohub_sdk.context import NeuroHubContext


def main():
    ctx = NeuroHubContext()
    try:
        spec = importlib.util.spec_from_file_location("inference", "/app/inference.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "run"):
            module.run(ctx)
            ctx.finalize("success")
        else:
            ctx.finalize("failure", "inference.py must define a run(ctx) function")
            sys.exit(1)
    except Exception as e:
        ctx.finalize("failure", f"{type(e).__name__}: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
