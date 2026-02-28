"""Pre-QC — Immediate data quality validation with fail-fast feedback.

Checks minimum requirements per modality and provides Korean error messages.
Designed to be synchronous/fast — users should NOT wait with bad data queued.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Thresholds
MAX_T1_VOXEL_MM = 1.5
MIN_T1_SLICES = 150
MIN_FMRI_VOLUMES = 100
MIN_DTI_DIRECTIONS = 30
MIN_PET_SLICES = 50


@dataclass
class PreQCCheck:
    """A single QC check result."""

    modality: str
    check_type: str
    status: str  # PASS, WARN, FAIL
    score: float | None = None
    message_ko: str = ""
    message_en: str = ""
    details: dict = field(default_factory=dict)


def check_minimum_requirements(
    json_sidecar: dict,
    nifti_shape: tuple[int, ...],
    modality: str,
    nifti_path: str | None = None,
) -> list[PreQCCheck]:
    """Immediate fail-fast checks per modality.

    Returns FAIL with Korean user-facing message if not met.
    """
    checks: list[PreQCCheck] = []

    if modality == "T1":
        checks.extend(_check_t1_requirements(json_sidecar, nifti_shape))
    elif modality == "PET":
        checks.extend(_check_pet_requirements(json_sidecar, nifti_shape))
    elif modality == "fMRI":
        checks.extend(_check_fmri_requirements(json_sidecar, nifti_shape))
    elif modality == "DTI":
        checks.extend(_check_dti_requirements(json_sidecar, nifti_shape, nifti_path))

    return checks


def _check_t1_requirements(sidecar: dict, shape: tuple[int, ...]) -> list[PreQCCheck]:
    checks = []

    # 3D acquisition check
    acq_type = sidecar.get("MRAcquisitionType", "")
    if acq_type != "3D":
        checks.append(PreQCCheck(
            modality="T1",
            check_type="ACQUISITION_TYPE",
            status="WARN",
            message_ko="3D 획득이 아닌 T1 영상입니다. FreeSurfer 분석 정확도가 저하될 수 있습니다.",
            message_en="T1 image is not 3D acquisition. FreeSurfer analysis accuracy may be reduced.",
            details={"acquisition_type": acq_type},
        ))

    # Max voxel dimension check
    max_voxel = _get_max_voxel(sidecar)
    if max_voxel is not None and max_voxel > MAX_T1_VOXEL_MM:
        checks.append(PreQCCheck(
            modality="T1",
            check_type="VOXEL_SIZE",
            status="FAIL",
            message_ko=f"복셀 크기가 {MAX_T1_VOXEL_MM}mm를 초과합니다 (현재: {max_voxel:.2f}mm).",
            message_en=f"Voxel size exceeds {MAX_T1_VOXEL_MM}mm (current: {max_voxel:.2f}mm).",
            details={"max_voxel_mm": max_voxel, "threshold_mm": MAX_T1_VOXEL_MM},
        ))
    elif max_voxel is not None:
        checks.append(PreQCCheck(
            modality="T1",
            check_type="VOXEL_SIZE",
            status="PASS",
            score=100.0 * (1.0 - max_voxel / MAX_T1_VOXEL_MM),
            message_ko=f"복셀 크기 양호 ({max_voxel:.2f}mm).",
            message_en=f"Voxel size OK ({max_voxel:.2f}mm).",
            details={"max_voxel_mm": max_voxel},
        ))

    # Slice count
    if len(shape) >= 3:
        slices = shape[2]
        if slices < MIN_T1_SLICES:
            checks.append(PreQCCheck(
                modality="T1",
                check_type="SLICE_COUNT",
                status="FAIL",
                message_ko=f"슬라이스 수가 {MIN_T1_SLICES}개 미만입니다 (현재: {slices}개).",
                message_en=f"Slice count below {MIN_T1_SLICES} (current: {slices}).",
                details={"slice_count": slices, "threshold": MIN_T1_SLICES},
            ))
        else:
            checks.append(PreQCCheck(
                modality="T1",
                check_type="SLICE_COUNT",
                status="PASS",
                message_ko=f"슬라이스 수 양호 ({slices}개).",
                message_en=f"Slice count OK ({slices}).",
                details={"slice_count": slices},
            ))

    return checks


def _check_pet_requirements(sidecar: dict, shape: tuple[int, ...]) -> list[PreQCCheck]:
    checks = []

    # Attenuation correction
    ac_method = sidecar.get("AttenuationCorrectionMethod", "")
    corrected_image = sidecar.get("CorrectedImage", [])
    image_type = sidecar.get("ImageType", [])
    it_str = " ".join(str(x).upper() for x in image_type) if isinstance(image_type, list) else str(image_type).upper()

    has_ac = bool(ac_method) or "ATTN" in str(corrected_image).upper() or "ATTN_CORR" in it_str
    if not has_ac:
        checks.append(PreQCCheck(
            modality="PET",
            check_type="ATTENUATION_CORRECTION",
            status="FAIL",
            message_ko="감쇠 보정(AC)이 적용되지 않은 PET 영상입니다.",
            message_en="PET image without attenuation correction (AC).",
            details={"ac_method": ac_method},
        ))
    else:
        checks.append(PreQCCheck(
            modality="PET",
            check_type="ATTENUATION_CORRECTION",
            status="PASS",
            message_ko="감쇠 보정(AC) 확인됨.",
            message_en="Attenuation correction confirmed.",
            details={"ac_method": ac_method or "detected"},
        ))

    # Tracer check
    tracer = sidecar.get("Radiopharmaceutical", sidecar.get("TracerName", ""))
    if not tracer:
        checks.append(PreQCCheck(
            modality="PET",
            check_type="TRACER_INFO",
            status="WARN",
            message_ko="방사성 의약품 정보가 누락되었습니다.",
            message_en="Radiopharmaceutical information missing.",
            details={},
        ))
    else:
        checks.append(PreQCCheck(
            modality="PET",
            check_type="TRACER_INFO",
            status="PASS",
            message_ko=f"방사성 의약품: {tracer}.",
            message_en=f"Radiopharmaceutical: {tracer}.",
            details={"tracer": tracer},
        ))

    # Slice count
    if len(shape) >= 3 and shape[2] < MIN_PET_SLICES:
        checks.append(PreQCCheck(
            modality="PET",
            check_type="SLICE_COUNT",
            status="FAIL",
            message_ko=f"PET 슬라이스 수가 {MIN_PET_SLICES}개 미만입니다 (현재: {shape[2]}개).",
            message_en=f"PET slice count below {MIN_PET_SLICES} (current: {shape[2]}).",
            details={"slice_count": shape[2], "threshold": MIN_PET_SLICES},
        ))

    return checks


def _check_fmri_requirements(sidecar: dict, shape: tuple[int, ...]) -> list[PreQCCheck]:
    checks = []

    # Volume count (4th dimension)
    if len(shape) >= 4:
        n_volumes = shape[3]
        if n_volumes < MIN_FMRI_VOLUMES:
            checks.append(PreQCCheck(
                modality="fMRI",
                check_type="VOLUME_COUNT",
                status="FAIL",
                message_ko=f"fMRI 볼륨이 {MIN_FMRI_VOLUMES}개 미만입니다 (현재: {n_volumes}개).",
                message_en=f"fMRI volumes below {MIN_FMRI_VOLUMES} (current: {n_volumes}).",
                details={"n_volumes": n_volumes, "threshold": MIN_FMRI_VOLUMES},
            ))
        else:
            checks.append(PreQCCheck(
                modality="fMRI",
                check_type="VOLUME_COUNT",
                status="PASS",
                message_ko=f"fMRI 볼륨 수 양호 ({n_volumes}개).",
                message_en=f"fMRI volume count OK ({n_volumes}).",
                details={"n_volumes": n_volumes},
            ))
    else:
        checks.append(PreQCCheck(
            modality="fMRI",
            check_type="VOLUME_COUNT",
            status="FAIL",
            message_ko="fMRI 데이터에 시간 차원이 없습니다.",
            message_en="fMRI data missing temporal dimension.",
            details={"shape": list(shape)},
        ))

    # RepetitionTime check
    tr = sidecar.get("RepetitionTime")
    if tr is None:
        checks.append(PreQCCheck(
            modality="fMRI",
            check_type="REPETITION_TIME",
            status="WARN",
            message_ko="RepetitionTime 정보가 누락되었습니다.",
            message_en="RepetitionTime information missing.",
        ))

    return checks


def _check_dti_requirements(
    sidecar: dict, shape: tuple[int, ...], nifti_path: str | None = None,
) -> list[PreQCCheck]:
    checks = []

    # Check diffusion directions (from 4th dim or bval count)
    if len(shape) >= 4:
        n_dirs = shape[3]
        if n_dirs < MIN_DTI_DIRECTIONS:
            checks.append(PreQCCheck(
                modality="DTI",
                check_type="DIFFUSION_DIRECTIONS",
                status="FAIL",
                message_ko=f"확산 방향이 {MIN_DTI_DIRECTIONS}개 미만입니다 (현재: {n_dirs}개).",
                message_en=f"Diffusion directions below {MIN_DTI_DIRECTIONS} (current: {n_dirs}).",
                details={"n_directions": n_dirs, "threshold": MIN_DTI_DIRECTIONS},
            ))
        else:
            checks.append(PreQCCheck(
                modality="DTI",
                check_type="DIFFUSION_DIRECTIONS",
                status="PASS",
                message_ko=f"확산 방향 수 양호 ({n_dirs}개).",
                message_en=f"Diffusion directions OK ({n_dirs}).",
                details={"n_directions": n_dirs},
            ))

    # Check bvec/bval files exist
    if nifti_path:
        import os
        bvec = nifti_path.replace(".nii.gz", ".bvec").replace(".nii", ".bvec")
        bval = nifti_path.replace(".nii.gz", ".bval").replace(".nii", ".bval")
        has_bvec = os.path.exists(bvec)
        has_bval = os.path.exists(bval)
        if not has_bvec or not has_bval:
            missing = []
            if not has_bvec:
                missing.append(".bvec")
            if not has_bval:
                missing.append(".bval")
            checks.append(PreQCCheck(
                modality="DTI",
                check_type="BVEC_BVAL_FILES",
                status="FAIL",
                message_ko=f"DTI 분석에 필요한 파일이 누락되었습니다: {', '.join(missing)}.",
                message_en=f"DTI analysis requires missing files: {', '.join(missing)}.",
                details={"missing_files": missing},
            ))
        else:
            checks.append(PreQCCheck(
                modality="DTI",
                check_type="BVEC_BVAL_FILES",
                status="PASS",
                message_ko=".bvec/.bval 파일 확인됨.",
                message_en=".bvec/.bval files confirmed.",
            ))

    return checks


def check_motion_severity(nifti_shape: tuple[int, ...], modality: str) -> PreQCCheck:
    """Flag motion issues — initially WARN only.

    Full motion detection requires temporal signal analysis (future phase).
    """
    return PreQCCheck(
        modality=modality,
        check_type="MOTION_SEVERITY",
        status="PASS",
        message_ko="움직임 검출: 추후 지원 예정.",
        message_en="Motion detection: coming in future phase.",
        details={"note": "Placeholder — full motion detection requires signal analysis"},
    )


def _get_max_voxel(sidecar: dict) -> float | None:
    """Get maximum voxel dimension from sidecar metadata."""
    dims = []

    slice_thickness = sidecar.get("SliceThickness")
    if slice_thickness is not None:
        dims.append(float(slice_thickness))

    pixel_spacing = sidecar.get("PixelSpacing")
    if isinstance(pixel_spacing, list) and len(pixel_spacing) >= 2:
        dims.extend(float(x) for x in pixel_spacing[:2])

    acq_voxel = sidecar.get("AcquisitionVoxelSize")
    if isinstance(acq_voxel, list):
        dims.extend(float(x) for x in acq_voxel)

    return max(dims) if dims else None


def evaluate_pre_qc_gate(checks: list[PreQCCheck]) -> tuple[bool, list[str], list[str]]:
    """Evaluate all checks and determine if analysis can proceed.

    Returns: (can_proceed, fail_messages, warn_messages)
    """
    fail_messages = []
    warn_messages = []

    for check in checks:
        if check.status == "FAIL":
            fail_messages.append(check.message_ko)
        elif check.status == "WARN":
            warn_messages.append(check.message_ko)

    can_proceed = len(fail_messages) == 0
    return can_proceed, fail_messages, warn_messages
