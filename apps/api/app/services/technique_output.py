"""Phase 4 — Technique output schema validation.

Standardised TechniqueOutput dataclass parsed from container logs or raw dicts.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

# Marker used by technique containers to emit structured output
_OUTPUT_MARKER = "NEUROHUB_OUTPUT:"


@dataclass
class TechniqueOutput:
    module: str
    module_version: str
    qc_score: float
    qc_flags: list[str] = field(default_factory=list)
    features: dict[str, float] = field(default_factory=dict)
    maps: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def validate_technique_output(raw: dict, expected_module: str) -> TechniqueOutput:
    """Validate a raw dict against the TechniqueOutput schema.

    Raises ValueError on missing/invalid fields or module mismatch.
    """
    missing = [k for k in ("module", "module_version", "qc_score") if k not in raw]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    qc = raw["qc_score"]
    if not isinstance(qc, (int, float)) or qc < 0 or qc > 100:
        raise ValueError(f"qc_score must be 0-100, got {qc}")

    if raw["module"] != expected_module:
        raise ValueError(
            f"Module mismatch: expected '{expected_module}', got '{raw['module']}'"
        )

    confidence = raw.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 100:
        raise ValueError(f"confidence must be 0-100, got {confidence}")

    return TechniqueOutput(
        module=raw["module"],
        module_version=str(raw["module_version"]),
        qc_score=float(qc),
        qc_flags=raw.get("qc_flags", []),
        features=raw.get("features", {}),
        maps=raw.get("maps", {}),
        confidence=float(confidence),
    )


def parse_technique_container_output(logs: str, technique_key: str) -> TechniqueOutput:
    """Extract TechniqueOutput from container log lines.

    Looks for lines starting with NEUROHUB_OUTPUT: followed by JSON.
    """
    for line in logs.splitlines():
        line = line.strip()
        if line.startswith(_OUTPUT_MARKER):
            json_str = line[len(_OUTPUT_MARKER):].strip()
            try:
                raw = json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON after {_OUTPUT_MARKER}: {e}") from e
            return validate_technique_output(raw, technique_key)

    raise ValueError(f"No {_OUTPUT_MARKER} line found in container logs")
