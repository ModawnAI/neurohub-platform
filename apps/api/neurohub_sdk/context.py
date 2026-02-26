"""NeuroHubContext — the interface expert inference scripts use."""
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("neurohub_sdk")


class NeuroHubContext:
    """Runtime context injected into expert inference scripts.

    Usage in inference.py:
        from neurohub_sdk import NeuroHubContext

        def run(ctx: NeuroHubContext):
            mri = ctx.get_input("mri_t1")
            model = ctx.load_model("weights.pt")
            result = analyze(mri, model)
            ctx.save_output("result_map", result)
            ctx.save_metric("confidence", 0.94)
    """

    def __init__(self):
        self._job_spec = self._load_job_spec()
        self._outputs: dict[str, Any] = {}
        self._metrics: dict[str, Any] = {}
        self._warnings: list[str] = []
        self._input_dir = Path(os.environ.get("NEUROHUB_INPUT_DIR", "/input"))
        self._output_dir = Path(os.environ.get("NEUROHUB_OUTPUT_DIR", "/output"))
        self._model_dir = Path(os.environ.get("NEUROHUB_MODEL_DIR", "/model"))

    def _load_job_spec(self) -> dict:
        import base64
        spec_b64 = os.environ.get("NEUROHUB_JOB_SPEC", "")
        if spec_b64:
            try:
                return json.loads(base64.b64decode(spec_b64))
            except Exception:
                pass
        return {}

    def get_input(self, slot_name: str) -> Path:
        """Get path to input file for given slot name."""
        inputs = self._job_spec.get("inputs", {})
        if slot_name in inputs:
            path = self._input_dir / inputs[slot_name].get("file_name", slot_name)
            if path.exists():
                return path
        # Fallback: look in /input directory
        for f in self._input_dir.iterdir():
            if slot_name.lower() in f.name.lower():
                return f
        raise FileNotFoundError(f"Input slot '{slot_name}' not found in {self._input_dir}")

    def get_option(self, key: str, default: Any = None) -> Any:
        """Get analysis option/parameter."""
        options = self._job_spec.get("options", {})
        return options.get(key, default)

    def load_model(self, filename: str) -> Path:
        """Get path to model weight file."""
        model_path = self._model_dir / filename
        if not model_path.exists():
            # Try input dir
            model_path = self._input_dir / filename
        if not model_path.exists():
            raise FileNotFoundError(f"Model file '{filename}' not found")
        return model_path

    def save_output(self, slot_name: str, data: Any, mime: str = "application/octet-stream"):
        """Save output. data can be a Path (file) or bytes."""
        if isinstance(data, Path):
            self._outputs[slot_name] = str(data)
        elif isinstance(data, bytes):
            out_path = self._output_dir / f"{slot_name}.bin"
            out_path.write_bytes(data)
            self._outputs[slot_name] = str(out_path)
        else:
            out_path = self._output_dir / f"{slot_name}.json"
            out_path.write_text(json.dumps(data))
            self._outputs[slot_name] = str(out_path)

    def save_metric(self, name: str, value: float):
        """Save a numeric metric (e.g. confidence, quality_score)."""
        self._metrics[name] = float(value)

    def add_warning(self, message: str):
        """Add a QC warning message."""
        self._warnings.append(message)

    def report_progress(self, pct: float, step: str = ""):
        """Report progress via callback (logs to stdout for now)."""
        logger.info("Progress: %.1f%% — %s", pct, step)

    def finalize(self, status: str = "success", error: str | None = None):
        """Emit final output JSON to stdout. Call at end of run()."""
        output = {
            "status": status,
            "outputs": self._outputs,
            "metrics": self._metrics,
            "qc": {
                "warnings": self._warnings,
                "quality_score": self._metrics.get("quality_score", 1.0),
            },
        }
        if error:
            output["error"] = error
            output["status"] = "failure"

        print("NEUROHUB_OUTPUT_START", flush=True)
        print(json.dumps(output), flush=True)
        print("NEUROHUB_OUTPUT_END", flush=True)
