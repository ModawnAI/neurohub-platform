"""Phase 8 — Pre-QC validation unit tests."""

import pytest

from app.services.pre_qc import (
    PreQCCheck,
    check_minimum_requirements,
    check_motion_severity,
    evaluate_pre_qc_gate,
)

pytestmark = pytest.mark.anyio


# --- MRI / T1 checks ---


def test_mri_pass():
    """Good T1 MRI passes all checks."""
    sidecar = {
        "MRAcquisitionType": "3D",
        "SliceThickness": 1.0,
        "PixelSpacing": [1.0, 1.0],
    }
    checks = check_minimum_requirements(sidecar, (256, 256, 176), "T1")
    assert all(c.status in ("PASS",) for c in checks)


def test_mri_voxel_too_large_fail():
    """T1 with max voxel > 1.5mm fails."""
    sidecar = {
        "MRAcquisitionType": "3D",
        "SliceThickness": 2.0,
        "PixelSpacing": [1.0, 1.0],
    }
    checks = check_minimum_requirements(sidecar, (256, 256, 176), "T1")
    voxel_check = next(c for c in checks if c.check_type == "VOXEL_SIZE")
    assert voxel_check.status == "FAIL"
    assert "1.5mm" in voxel_check.message_ko


def test_mri_low_slices_fail():
    """T1 with < 150 slices fails."""
    sidecar = {
        "MRAcquisitionType": "3D",
        "SliceThickness": 1.0,
        "PixelSpacing": [1.0, 1.0],
    }
    checks = check_minimum_requirements(sidecar, (256, 256, 100), "T1")
    slice_check = next(c for c in checks if c.check_type == "SLICE_COUNT")
    assert slice_check.status == "FAIL"


def test_mri_2d_warns():
    """2D T1 acquisition triggers WARN."""
    sidecar = {
        "MRAcquisitionType": "2D",
        "SliceThickness": 1.0,
        "PixelSpacing": [1.0, 1.0],
    }
    checks = check_minimum_requirements(sidecar, (256, 256, 176), "T1")
    acq_check = next(c for c in checks if c.check_type == "ACQUISITION_TYPE")
    assert acq_check.status == "WARN"


# --- PET checks ---


def test_pet_pass():
    """Valid FDG PET passes."""
    sidecar = {
        "AttenuationCorrectionMethod": "CT",
        "Radiopharmaceutical": "FDG",
    }
    checks = check_minimum_requirements(sidecar, (128, 128, 89), "PET")
    ac_check = next(c for c in checks if c.check_type == "ATTENUATION_CORRECTION")
    assert ac_check.status == "PASS"


def test_pet_missing_ac_fail():
    """PET without AC fails."""
    sidecar = {
        "Radiopharmaceutical": "FDG",
    }
    checks = check_minimum_requirements(sidecar, (128, 128, 89), "PET")
    ac_check = next(c for c in checks if c.check_type == "ATTENUATION_CORRECTION")
    assert ac_check.status == "FAIL"
    assert "감쇠 보정" in ac_check.message_ko


def test_pet_missing_tracer_warn():
    """PET without tracer info warns."""
    sidecar = {
        "AttenuationCorrectionMethod": "CT",
    }
    checks = check_minimum_requirements(sidecar, (128, 128, 89), "PET")
    tracer_check = next(c for c in checks if c.check_type == "TRACER_INFO")
    assert tracer_check.status == "WARN"


# --- fMRI checks ---


def test_fmri_pass():
    """fMRI with >= 100 volumes passes."""
    sidecar = {"RepetitionTime": 2.0}
    checks = check_minimum_requirements(sidecar, (64, 64, 40, 200), "fMRI")
    vol_check = next(c for c in checks if c.check_type == "VOLUME_COUNT")
    assert vol_check.status == "PASS"


def test_fmri_low_volumes_fail():
    """fMRI with < 100 volumes fails."""
    sidecar = {"RepetitionTime": 2.0}
    checks = check_minimum_requirements(sidecar, (64, 64, 40, 80), "fMRI")
    vol_check = next(c for c in checks if c.check_type == "VOLUME_COUNT")
    assert vol_check.status == "FAIL"
    assert "100" in vol_check.message_ko


def test_fmri_no_temporal_dim_fail():
    """fMRI without 4th dimension fails."""
    sidecar = {"RepetitionTime": 2.0}
    checks = check_minimum_requirements(sidecar, (64, 64, 40), "fMRI")
    vol_check = next(c for c in checks if c.check_type == "VOLUME_COUNT")
    assert vol_check.status == "FAIL"


# --- DTI checks ---


def test_dti_pass():
    """DTI with >= 30 directions passes."""
    checks = check_minimum_requirements({}, (128, 128, 70, 64), "DTI")
    dir_check = next(c for c in checks if c.check_type == "DIFFUSION_DIRECTIONS")
    assert dir_check.status == "PASS"


def test_dti_low_directions_fail():
    """DTI with < 30 directions fails."""
    checks = check_minimum_requirements({}, (128, 128, 70, 15), "DTI")
    dir_check = next(c for c in checks if c.check_type == "DIFFUSION_DIRECTIONS")
    assert dir_check.status == "FAIL"


# --- Motion detection (placeholder) ---


def test_motion_detection_placeholder():
    result = check_motion_severity((256, 256, 176), "T1")
    assert result.status == "PASS"
    assert result.check_type == "MOTION_SEVERITY"


# --- Pre-QC gate evaluation ---


def test_pre_qc_gate_all_pass():
    checks = [
        PreQCCheck(modality="T1", check_type="VOXEL_SIZE", status="PASS", message_ko="OK"),
        PreQCCheck(modality="T1", check_type="SLICE_COUNT", status="PASS", message_ko="OK"),
    ]
    can_proceed, fails, warns = evaluate_pre_qc_gate(checks)
    assert can_proceed is True
    assert len(fails) == 0


def test_pre_qc_gate_fail_blocks():
    checks = [
        PreQCCheck(modality="T1", check_type="VOXEL_SIZE", status="FAIL",
                   message_ko="복셀 크기가 1.5mm를 초과합니다"),
        PreQCCheck(modality="T1", check_type="SLICE_COUNT", status="PASS", message_ko="OK"),
    ]
    can_proceed, fails, warns = evaluate_pre_qc_gate(checks)
    assert can_proceed is False
    assert len(fails) == 1
    assert "1.5mm" in fails[0]


def test_pre_qc_gate_warn_passes():
    checks = [
        PreQCCheck(modality="T1", check_type="ACQUISITION_TYPE", status="WARN",
                   message_ko="3D 획득이 아닌 T1 영상입니다"),
        PreQCCheck(modality="T1", check_type="VOXEL_SIZE", status="PASS", message_ko="OK"),
    ]
    can_proceed, fails, warns = evaluate_pre_qc_gate(checks)
    assert can_proceed is True
    assert len(warns) == 1


# --- Acquisition Suitability Selector tests ---


def test_t1_non_isotropic_passes_if_max_under_threshold():
    """Non-isotropic T1 (e.g. 0.5x0.5x1.2mm) passes if max voxel <= 1.5mm."""
    sidecar = {
        "MRAcquisitionType": "3D",
        "SliceThickness": 1.2,
        "PixelSpacing": [0.5, 0.5],
    }
    checks = check_minimum_requirements(sidecar, (512, 512, 160), "T1")
    voxel_check = next(c for c in checks if c.check_type == "VOXEL_SIZE")
    assert voxel_check.status == "PASS"
    assert voxel_check.details["max_voxel_mm"] == 1.2


def test_t1_thickest_axis_exceeds_threshold():
    """T1 with thickest axis > 1.5mm fails even if other axes are fine."""
    sidecar = {
        "MRAcquisitionType": "3D",
        "SliceThickness": 1.8,
        "PixelSpacing": [0.9, 0.9],
    }
    checks = check_minimum_requirements(sidecar, (256, 256, 176), "T1")
    voxel_check = next(c for c in checks if c.check_type == "VOXEL_SIZE")
    assert voxel_check.status == "FAIL"
    assert "1.5mm" in voxel_check.message_ko


def test_fmri_exactly_100_volumes_passes():
    """fMRI with exactly 100 time points passes."""
    sidecar = {"RepetitionTime": 2.0}
    checks = check_minimum_requirements(sidecar, (64, 64, 40, 100), "fMRI")
    vol_check = next(c for c in checks if c.check_type == "VOLUME_COUNT")
    assert vol_check.status == "PASS"


def test_fmri_99_volumes_fails():
    """fMRI with 99 time points (< 100) fails."""
    sidecar = {"RepetitionTime": 2.0}
    checks = check_minimum_requirements(sidecar, (64, 64, 40, 99), "fMRI")
    vol_check = next(c for c in checks if c.check_type == "VOLUME_COUNT")
    assert vol_check.status == "FAIL"


def test_dti_missing_bvec_bval_fails():
    """DTI without bvec/bval files triggers FAIL."""
    checks = check_minimum_requirements(
        {}, (128, 128, 70, 64), "DTI",
        nifti_path="/tmp/nonexistent_dti.nii.gz",
    )
    bvec_check = next((c for c in checks if c.check_type == "BVEC_BVAL_FILES"), None)
    assert bvec_check is not None
    assert bvec_check.status == "FAIL"
    assert ".bvec" in bvec_check.message_ko


def test_pet_low_slices_fails():
    """PET with < 50 slices fails."""
    sidecar = {
        "AttenuationCorrectionMethod": "CT",
        "Radiopharmaceutical": "FDG",
    }
    checks = check_minimum_requirements(sidecar, (128, 128, 30), "PET")
    slice_check = next((c for c in checks if c.check_type == "SLICE_COUNT"), None)
    assert slice_check is not None
    assert slice_check.status == "FAIL"


def test_multiple_modality_checks_aggregated():
    """Multiple checks from different modalities combine correctly in gate."""
    t1_checks = check_minimum_requirements(
        {"MRAcquisitionType": "3D", "SliceThickness": 1.0, "PixelSpacing": [1.0, 1.0]},
        (256, 256, 176), "T1",
    )
    pet_checks = check_minimum_requirements(
        {},  # no AC → FAIL
        (128, 128, 89), "PET",
    )
    all_checks = t1_checks + pet_checks
    can_proceed, fails, warns = evaluate_pre_qc_gate(all_checks)
    assert can_proceed is False
    assert any("감쇠 보정" in f for f in fails)
