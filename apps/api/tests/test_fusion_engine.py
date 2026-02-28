"""Phase 5 — Fusion Engine tests."""

import json
import logging

import pytest

from app.services.fusion_engine import FusionConfig, FusionResult, run_fusion
from app.services.technique_output import TechniqueOutput


def _make_output(module: str, qc: float = 85.0, features: dict | None = None, maps: dict | None = None) -> TechniqueOutput:
    return TechniqueOutput(
        module=module,
        module_version="1.0.0",
        qc_score=qc,
        qc_flags=[],
        features={"metric_a": 1.0, "metric_b": 2.0} if features is None else features,
        maps=maps if maps is not None else {},
        confidence=qc,
    )


def test_basic_two_module_fusion():
    outputs = [
        _make_output("FDG_PET", qc=80, features={"suvr": 1.2}),
        _make_output("Cortical_Thickness", qc=90, features={"suvr": 0.8}),
    ]
    config = FusionConfig(
        service_id="test-svc",
        technique_weights={"FDG_PET": 0.5, "Cortical_Thickness": 0.5},
    )
    result = run_fusion(outputs, config)
    assert len(result.included_modules) == 2
    assert "suvr" in result.results
    assert result.confidence_score == 85.0  # mean(80, 90)


def test_qc_weight_adjustment():
    outputs = [_make_output("FDG_PET", qc=80, features={"val": 10.0})]
    config = FusionConfig(
        service_id="test",
        technique_weights={"FDG_PET": 1.0},
    )
    result = run_fusion(outputs, config)
    # Single module: w_adjusted = 1.0 * (80/100) = 0.8
    assert result.included_modules == ["FDG_PET"]
    assert result.confidence_score == 80.0


def test_excludes_low_qc_module():
    outputs = [
        _make_output("FDG_PET", qc=30),
        _make_output("VBM", qc=85),
    ]
    config = FusionConfig(
        service_id="test",
        technique_weights={"FDG_PET": 0.5, "VBM": 0.5},
        qc_fail_threshold=40.0,
    )
    result = run_fusion(outputs, config)
    assert "FDG_PET" not in result.included_modules
    assert "VBM" in result.included_modules
    assert len(result.excluded_modules) == 1
    assert result.excluded_modules[0]["module"] == "FDG_PET"
    assert result.excluded_modules[0]["reason"] == "qc_below_threshold"


def test_all_excluded_raises():
    outputs = [
        _make_output("FDG_PET", qc=20),
        _make_output("VBM", qc=30),
    ]
    config = FusionConfig(
        service_id="test",
        technique_weights={"FDG_PET": 0.5, "VBM": 0.5},
        qc_fail_threshold=40.0,
    )
    with pytest.raises(ValueError, match="All.*modules excluded"):
        run_fusion(outputs, config)


def test_single_module_concordance_is_1():
    outputs = [_make_output("FDG_PET", qc=90)]
    config = FusionConfig(
        service_id="test",
        technique_weights={"FDG_PET": 1.0},
    )
    result = run_fusion(outputs, config)
    assert result.concordance_score == 1.0


def test_concordance_3_of_5():
    outputs = [
        _make_output("A", qc=80),
        _make_output("B", qc=85),
        _make_output("C", qc=90),
        _make_output("D", qc=20),  # excluded
        _make_output("E", qc=10),  # excluded
    ]
    config = FusionConfig(
        service_id="test",
        technique_weights={"A": 0.2, "B": 0.2, "C": 0.2, "D": 0.2, "E": 0.2},
    )
    result = run_fusion(outputs, config)
    assert result.concordance_score == 0.6


def test_confidence_is_mean_qc():
    outputs = [
        _make_output("A", qc=70),
        _make_output("B", qc=80),
        _make_output("C", qc=90),
    ]
    config = FusionConfig(
        service_id="test",
        technique_weights={"A": 0.33, "B": 0.34, "C": 0.33},
    )
    result = run_fusion(outputs, config)
    assert result.confidence_score == 80.0  # mean(70, 80, 90)


def test_z_score_normalization():
    """Two modules with features [10, 20] → z-scores [-1, 1]."""
    outputs = [
        _make_output("A", qc=100, features={"val": 10.0}),
        _make_output("B", qc=100, features={"val": 20.0}),
    ]
    config = FusionConfig(
        service_id="test",
        technique_weights={"A": 0.5, "B": 0.5},
    )
    result = run_fusion(outputs, config)
    # Equal weights + equal QC → weighted mean of z-scores = 0
    assert abs(result.results["val"]) < 0.01


def test_empty_features_handled():
    outputs = [
        _make_output("A", qc=80, features={}),
        _make_output("B", qc=90, features={}),
    ]
    config = FusionConfig(
        service_id="test",
        technique_weights={"A": 0.5, "B": 0.5},
    )
    result = run_fusion(outputs, config)
    assert result.results == {}


def test_weight_sum_warning_logged(caplog):
    outputs = [_make_output("A", qc=90)]
    config = FusionConfig(
        service_id="test",
        technique_weights={"A": 0.7},  # doesn't sum to 1.0
    )
    with caplog.at_level(logging.WARNING):
        run_fusion(outputs, config)
    assert "weights sum to" in caplog.text.lower()


def test_result_json_serializable():
    outputs = [
        _make_output("FDG_PET", qc=85, features={"suvr": 1.2}, maps={"map": "/path.nii"}),
    ]
    config = FusionConfig(
        service_id="test",
        technique_weights={"FDG_PET": 1.0},
    )
    result = run_fusion(outputs, config)
    serialized = json.dumps(result.to_dict())
    parsed = json.loads(serialized)
    assert parsed["service_id"] == "test"
    assert "FDG_PET__map" in parsed["probability_maps"]


def test_epilepsy_lesion_12_module_fusion():
    """Simulate Epilepsy Lesion Analysis with 12 technique modules using real-ish weights."""
    techniques = {
        "FDG_PET": 0.12, "SPECT_SISCOM": 0.10, "Cortical_Thickness": 0.08,
        "VBM": 0.08, "Diffusion_Properties": 0.07, "Tractography": 0.07,
        "EEG_Source": 0.10, "EEG_Connectivity": 0.08, "MEG_Source": 0.10,
        "MEG_Connectivity": 0.08, "fMRI_Task": 0.06, "fMRI_Connectivity": 0.06,
    }
    outputs = [
        _make_output(key, qc=75 + i * 2, features={"lesion_score": 0.5 + i * 0.03})
        for i, key in enumerate(techniques)
    ]
    config = FusionConfig(
        service_id="epilepsy_lesion",
        technique_weights=techniques,
    )
    result = run_fusion(outputs, config)
    assert len(result.included_modules) == 12
    assert result.concordance_score == 1.0
    assert 75 < result.confidence_score < 100
    assert "lesion_score" in result.results
