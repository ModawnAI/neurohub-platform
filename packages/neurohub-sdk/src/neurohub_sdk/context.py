"""Input and Output contexts for service execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


_SENTINEL = object()


@dataclass
class InputContext:
    """Typed access to all inputs, files, demographics, and options for a run."""

    run_id: str
    request_id: str
    case_id: str
    inputs: dict[str, Any]
    demographics: dict[str, Any]
    options: dict[str, Any]
    files: dict[str, dict[str, Any]]  # slot_key -> {storage_path, presigned_url}
    storage_config: dict[str, Any]
    _http_client: Any = field(default=None, repr=False)
    _file_cache: dict[str, bytes] = field(default_factory=dict, repr=False)

    def get_input(self, key: str, *, default: Any = _SENTINEL) -> Any:
        if key in self.inputs:
            return self.inputs[key]
        if default is not _SENTINEL:
            return default
        raise KeyError(f"Input '{key}' not found. Available: {list(self.inputs.keys())}")

    def get_option(self, key: str, *, default: Any = None) -> Any:
        return self.options.get(key, default)

    def has_file(self, slot_key: str) -> bool:
        return slot_key in self.files

    async def get_file(self, slot_key: str) -> bytes:
        """Download file bytes from presigned URL (cached)."""
        if slot_key in self._file_cache:
            return self._file_cache[slot_key]

        file_info = self.files.get(slot_key)
        if not file_info:
            raise KeyError(f"File slot '{slot_key}' not found. Available: {list(self.files.keys())}")

        url = file_info.get("presigned_url")
        if not url:
            raise ValueError(f"No presigned URL for file slot '{slot_key}'")

        import httpx

        client = self._http_client or httpx.AsyncClient(timeout=60)
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.content
        finally:
            if not self._http_client:
                await client.aclose()

        self._file_cache[slot_key] = data
        return data

    def create_output(self) -> "OutputContext":
        return OutputContext(run_id=self.run_id)

    @classmethod
    def from_job_spec(cls, job_spec: dict) -> "InputContext":
        """Build InputContext from a standard NeuroHub JobSpec dict."""
        # Build files dict from input_artifacts + presigned_urls
        artifacts = job_spec.get("input_artifacts", {})
        presigned = job_spec.get("presigned_urls", {})
        files = {}
        for slot_key, storage_path in artifacts.items():
            files[slot_key] = {
                "storage_path": storage_path,
                "presigned_url": presigned.get(slot_key),
            }

        return cls(
            run_id=job_spec.get("run_id", ""),
            request_id=job_spec.get("request_id", ""),
            case_id=job_spec.get("case_id", ""),
            inputs=job_spec.get("user_inputs", {}),
            demographics=job_spec.get("case_demographics", {}),
            options=job_spec.get("user_options", {}),
            files=files,
            storage_config=job_spec.get("storage", {}),
        )


class OutputContext:
    """Structured output builder for service results."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._results: dict[str, Any] = {}
        self._files: dict[str, dict[str, Any]] = {}
        self._metrics: dict[str, Any] = {}
        self._error: dict[str, Any] | None = None

    def set(self, key: str, value: Any) -> None:
        self._results[key] = value

    def set_file(
        self,
        key: str,
        data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
    ) -> None:
        self._files[key] = {
            "data": data,
            "filename": filename,
            "content_type": content_type,
            "size": len(data),
        }

    def set_metric(self, key: str, value: float | int) -> None:
        self._metrics[key] = value

    def set_error(self, message: str, *, code: str = "SERVICE_ERROR") -> None:
        self._error = {"message": message, "code": code}

    @property
    def status(self) -> str:
        return "FAILED" if self._error else "SUCCEEDED"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "run_id": self.run_id,
            "status": self.status,
            "results": self._results,
            "files": {
                k: {
                    "filename": v["filename"],
                    "content_type": v["content_type"],
                    "size": v["size"],
                }
                for k, v in self._files.items()
            },
            "metrics": self._metrics,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        if self._error:
            d["error"] = self._error
        return d

    def to_result_manifest(self) -> dict[str, Any]:
        """Produce a result_manifest compatible with the Run model."""
        return {
            "status": "completed" if not self._error else "failed",
            "results": self._results,
            "files": {
                k: {
                    "filename": v["filename"],
                    "content_type": v["content_type"],
                    "size": v["size"],
                }
                for k, v in self._files.items()
            },
            "metrics": self._metrics,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error": self._error,
        }

    def get_file_data(self, key: str) -> bytes | None:
        """Get raw file bytes for upload to storage."""
        info = self._files.get(key)
        return info["data"] if info else None
