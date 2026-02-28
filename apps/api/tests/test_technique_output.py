"""Phase 4 — TechniqueOutput validation tests."""

import json

import pytest

from app.services.technique_output import (
    TechniqueOutput,
    parse_technique_container_output,
    validate_technique_output,
)

VALID_RAW = {
    "module": "FDG_PET",
    "module_version": "1.0.0",
    "qc_score": 85.0,
    "qc_flags": ["MILD_MOTION"],
    "features": {"global_suvr": 1.23, "frontal_suvr": 1.1},
    "maps": {"suvr_map": "/outputs/suvr.nii.gz", "zscore_map": "/outputs/zscore.nii.gz"},
    "confidence": 78.5,
}


def test_valid_output_parses_correctly():
    out = validate_technique_output(VALID_RAW, "FDG_PET")
    assert out.module == "FDG_PET"
    assert out.module_version == "1.0.0"
    assert out.qc_score == 85.0
    assert out.qc_flags == ["MILD_MOTION"]
    assert out.features["global_suvr"] == 1.23
    assert out.maps["suvr_map"] == "/outputs/suvr.nii.gz"
    assert out.confidence == 78.5


def test_missing_module_raises():
    raw = {k: v for k, v in VALID_RAW.items() if k != "module"}
    with pytest.raises(ValueError, match="Missing required fields.*module"):
        validate_technique_output(raw, "FDG_PET")


def test_qc_score_out_of_range():
    raw = {**VALID_RAW, "qc_score": 150}
    with pytest.raises(ValueError, match="qc_score must be 0-100"):
        validate_technique_output(raw, "FDG_PET")

    raw2 = {**VALID_RAW, "qc_score": -5}
    with pytest.raises(ValueError, match="qc_score must be 0-100"):
        validate_technique_output(raw2, "FDG_PET")


def test_empty_features_valid():
    raw = {**VALID_RAW, "features": {}}
    out = validate_technique_output(raw, "FDG_PET")
    assert out.features == {}


def test_parse_from_container_logs():
    logs = (
        "INFO: Starting FDG_PET analysis...\n"
        "INFO: Processing complete.\n"
        f"NEUROHUB_OUTPUT: {json.dumps(VALID_RAW)}\n"
        "INFO: Container exiting.\n"
    )
    out = parse_technique_container_output(logs, "FDG_PET")
    assert out.module == "FDG_PET"
    assert out.qc_score == 85.0


def test_no_json_in_logs_handled():
    logs = "INFO: no output marker here\nDONE\n"
    with pytest.raises(ValueError, match="No NEUROHUB_OUTPUT"):
        parse_technique_container_output(logs, "FDG_PET")


def test_module_mismatch_raises():
    raw = {**VALID_RAW, "module": "Amyloid_PET"}
    with pytest.raises(ValueError, match="Module mismatch"):
        validate_technique_output(raw, "FDG_PET")


def test_output_serializes_to_json():
    out = validate_technique_output(VALID_RAW, "FDG_PET")
    serialized = json.dumps(out.to_dict())
    parsed = json.loads(serialized)
    assert parsed["module"] == "FDG_PET"
    assert parsed["features"]["global_suvr"] == 1.23
