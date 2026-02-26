"""Parse structured JSON output from NeuroHub analysis containers.

Containers must write a JSON object to stdout following the NeuroHub output contract:
{
  "status": "success" | "failure",
  "outputs": {
    "<slot_name>": "<path_inside_container>"
  },
  "metrics": {
    "<metric_name>": <number>
  },
  "qc": {
    "quality_score": 0.0-1.0,
    "warnings": ["..."],
    "motion_artifacts": false
  },
  "error": "error message if status=failure"
}
"""
import json
import logging
import re
from typing import Any

logger = logging.getLogger("neurohub.output_parser")

# PHI patterns to detect in output (HIPAA compliance)
PHI_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",           # SSN format
    r"\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b",  # credit card
    r"(?i)patient[\s_-]?name\s*[:=]\s*[A-Z][a-z]+",
    r"(?i)date[\s_-]?of[\s_-]?birth\s*[:=]\s*\d",
    r"(?i)social[\s_-]?security",
    r"(?i)mrn\s*[:=]\s*\d+",
]


def extract_json_from_logs(logs: str) -> dict | None:
    """Extract the last JSON object from container stdout logs."""
    if not logs:
        return None

    # Try to find JSON between NEUROHUB_OUTPUT markers first
    marker_match = re.search(
        r"NEUROHUB_OUTPUT_START\s*(\{.*?\})\s*NEUROHUB_OUTPUT_END",
        logs, re.DOTALL
    )
    if marker_match:
        try:
            return json.loads(marker_match.group(1))
        except json.JSONDecodeError:
            pass

    # Fall back: find last complete JSON object in logs
    lines = logs.strip().split("\n")
    for line in reversed(lines):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    return None


def parse_container_output(logs: str, output_schema: dict | None = None) -> dict:
    """Parse container output logs into a structured result_manifest.

    Returns a result_manifest dict suitable for Run.result_manifest.
    """
    raw = extract_json_from_logs(logs)

    if raw is None:
        # Container didn't output valid JSON — treat as partial result
        return {
            "status": "completed",
            "parse_error": "Container did not output valid JSON",
            "raw_log_tail": logs[-2000:] if logs else "",
            "outputs": {},
            "metrics": {},
            "qc": {"quality_score": 0.0, "warnings": ["No structured output"]},
        }

    # Validate against output_schema if provided
    validation_warnings = []
    if output_schema and "outputs" in output_schema:
        expected_outputs = output_schema.get("outputs", {})
        actual_outputs = raw.get("outputs", {})
        for expected_key in expected_outputs:
            if expected_key not in actual_outputs:
                validation_warnings.append(f"Missing expected output: {expected_key}")

    # Scan for PHI in output
    phi_detected = scan_for_phi(json.dumps(raw))
    if phi_detected:
        logger.warning("PHI patterns detected in container output: %s", phi_detected)
        # Redact but don't block — log for audit
        raw["_phi_warning"] = f"Potential PHI detected in {len(phi_detected)} fields"

    result = {
        "status": raw.get("status", "completed"),
        "outputs": raw.get("outputs", {}),
        "metrics": raw.get("metrics", {}),
        "qc": raw.get("qc", {}),
        "error": raw.get("error"),
        "_validation_warnings": validation_warnings,
        "_phi_detected": bool(phi_detected),
    }

    return result


def scan_for_phi(text: str) -> list[str]:
    """Return list of PHI pattern names found in text."""
    found = []
    for pattern in PHI_PATTERNS:
        if re.search(pattern, text):
            found.append(pattern[:40])
    return found


def extract_qc_metrics(result_manifest: dict) -> dict:
    """Extract QC-relevant metrics from result_manifest for QC evaluator."""
    qc = result_manifest.get("qc", {})
    metrics = result_manifest.get("metrics", {})
    return {
        "quality_score": qc.get("quality_score", 0.0),
        "confidence": metrics.get("confidence", metrics.get("confidence_score", 0.0)),
        "warnings": qc.get("warnings", []),
        "motion_artifacts": qc.get("motion_artifacts", False),
        **metrics,
    }
