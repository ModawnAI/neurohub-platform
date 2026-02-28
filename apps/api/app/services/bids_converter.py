"""BIDS Converter — DICOM → NIfTI → BIDS pipeline.

Uses dcm2niix for DICOM→NIfTI conversion, then classifies modality
from JSON sidecars and organizes into BIDS directory structure.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_VOLUME_SLICES = 100
MIN_T1_SLICES = 150
MAX_T1_VOXEL_MM = 1.5
MIN_FMRI_VOLUMES = 100
MIN_DTI_DIRECTIONS = 30


@dataclass
class NiftiVolume:
    """Represents a converted NIfTI volume with metadata."""

    nifti_path: str
    json_sidecar: dict
    shape: tuple[int, ...] = ()
    modality_tag: str = "UNKNOWN"
    skip_reason: str | None = None


@dataclass
class BidsOrganizationResult:
    """Result of BIDS organization."""

    bids_dir: str
    selected: dict[str, NiftiVolume] = field(default_factory=dict)
    skipped: list[NiftiVolume] = field(default_factory=list)
    validation_errors: list[dict] = field(default_factory=list)


async def decompress_upload(zip_path: str, output_dir: str) -> str:
    """Extract a zip upload to output_dir. Returns the extracted directory path."""
    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"Not a valid zip file: {zip_path}")

    extract_dir = os.path.join(output_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)

    def _extract():
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

    await asyncio.to_thread(_extract)
    logger.info("Decompressed %s to %s", zip_path, extract_dir)
    return extract_dir


async def convert_dicom_to_nifti(dicom_dir: str, output_dir: str) -> list[NiftiVolume]:
    """Run dcm2niix on a DICOM directory.

    Returns list of NiftiVolume with paths and JSON sidecar data.
    """
    os.makedirs(output_dir, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        "dcm2niix",
        "-b", "y",       # generate BIDS sidecar
        "-z", "y",       # gzip compress
        "-f", "%p_%s",   # naming: protocol_series
        "-o", output_dir,
        dicom_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"dcm2niix failed: {stderr.decode()}")

    volumes = []
    output_path = Path(output_dir)

    for nifti_file in sorted(output_path.glob("*.nii.gz")):
        json_file = nifti_file.with_suffix("").with_suffix(".json")
        sidecar = {}
        if json_file.exists():
            with open(json_file) as f:
                sidecar = json.load(f)

        shape = _get_nifti_shape(str(nifti_file))
        modality = classify_modality(sidecar)

        volumes.append(NiftiVolume(
            nifti_path=str(nifti_file),
            json_sidecar=sidecar,
            shape=shape,
            modality_tag=modality,
        ))

    logger.info("dcm2niix converted %d volumes from %s", len(volumes), dicom_dir)
    return volumes


def _get_nifti_shape(nifti_path: str) -> tuple[int, ...]:
    """Get NIfTI volume shape. Returns empty tuple if nibabel not available."""
    try:
        import nibabel as nib
        img = nib.load(nifti_path)
        return tuple(img.shape)
    except ImportError:
        logger.warning("nibabel not installed, cannot read NIfTI shape")
        return ()
    except Exception as e:
        logger.warning("Failed to read NIfTI shape for %s: %s", nifti_path, e)
        return ()


def classify_modality(json_sidecar: dict) -> str:
    """Classify modality from dcm2niix JSON sidecar.

    Returns: T1, T2, FLAIR, PET, fMRI, DTI, EEG, UNKNOWN
    """
    modality = json_sidecar.get("Modality", "").upper()
    series_desc = json_sidecar.get("SeriesDescription", "").upper()
    seq_name = json_sidecar.get("SequenceName", "").upper()
    image_type = json_sidecar.get("ImageType", [])
    if isinstance(image_type, list):
        image_type = " ".join(str(x).upper() for x in image_type)
    else:
        image_type = str(image_type).upper()

    # PET
    if modality == "PT":
        return "PET"

    # MRI subtypes
    if modality in ("MR", "MRI", ""):
        # fMRI: has RepetitionTime and multiple volumes
        rep_time = json_sidecar.get("RepetitionTime")
        if rep_time and any(kw in series_desc for kw in ("BOLD", "FMRI", "RESTING", "TASK")):
            return "fMRI"

        # DTI: has diffusion info
        if any(kw in series_desc for kw in ("DTI", "DWI", "DIFFUSION", "TENSOR")):
            return "DTI"

        # FLAIR
        if "FLAIR" in series_desc:
            return "FLAIR"

        # T2
        if "T2" in series_desc and "FLAIR" not in series_desc:
            return "T2"

        # T1 (default for MPRAGE, SPGR, BRAVO, or explicit T1)
        if any(kw in series_desc for kw in ("T1", "MPRAGE", "SPGR", "BRAVO", "IR-FSPGR")):
            return "T1"
        if any(kw in seq_name for kw in ("MPRAGE", "SPGR", "BRAVO")):
            return "T1"

        # Default MR → T1 if 3D acquisition
        acq_type = json_sidecar.get("MRAcquisitionType", "")
        if acq_type == "3D":
            return "T1"

        return "MRI_OTHER"

    # EEG
    if modality == "EEG":
        return "EEG"

    return "UNKNOWN"


def filter_by_slice_count(
    volumes: list[NiftiVolume],
    min_slices: int = MIN_VOLUME_SLICES,
) -> tuple[list[NiftiVolume], list[NiftiVolume]]:
    """Filter volumes by minimum slice count.

    Returns (valid, skipped) — skipped volumes get skip_reason set.
    """
    valid = []
    skipped = []

    for vol in volumes:
        if len(vol.shape) < 3:
            vol.skip_reason = "SKIPPED_NOT_3D"
            skipped.append(vol)
            continue

        slice_count = vol.shape[2]
        if slice_count < min_slices:
            vol.skip_reason = f"SKIPPED_LOW_SLICES ({slice_count} < {min_slices})"
            skipped.append(vol)
        else:
            valid.append(vol)

    return valid, skipped


def select_best_t1_for_freesurfer(candidates: list[NiftiVolume]) -> NiftiVolume | None:
    """From T1 candidates, pick the best for FreeSurfer recon-all.

    Criteria:
    - MRAcquisitionType == "3D"
    - SeriesDescription contains MPRAGE, SPGR, BRAVO, or T1
    - max(SliceThickness, PixelSpacing) <= 1.5mm
    - >= 150 slices
    - Prefer smallest max voxel dimension
    """
    valid = []
    for vol in candidates:
        if vol.modality_tag != "T1":
            continue

        sidecar = vol.json_sidecar
        acq_type = sidecar.get("MRAcquisitionType", "")
        if acq_type != "3D":
            continue

        # Check slice count
        if len(vol.shape) < 3 or vol.shape[2] < MIN_T1_SLICES:
            continue

        # Check max voxel dimension
        max_voxel = _get_max_voxel_mm(sidecar)
        if max_voxel is None or max_voxel > MAX_T1_VOXEL_MM:
            continue

        valid.append((vol, max_voxel))

    if not valid:
        return None

    # Prefer smallest max voxel
    valid.sort(key=lambda x: x[1])
    return valid[0][0]


def _get_max_voxel_mm(sidecar: dict) -> float | None:
    """Get the maximum voxel dimension in mm from sidecar."""
    slice_thickness = sidecar.get("SliceThickness")
    pixel_spacing = sidecar.get("PixelSpacing", sidecar.get("InPlanePhaseEncodingDirection"))

    dims = []
    if slice_thickness is not None:
        dims.append(float(slice_thickness))

    if isinstance(pixel_spacing, list) and len(pixel_spacing) >= 2:
        dims.extend(float(x) for x in pixel_spacing[:2])
    elif isinstance(pixel_spacing, (int, float)):
        dims.append(float(pixel_spacing))

    # Also check AcquisitionVoxelSize (some sidecars)
    acq_voxel = sidecar.get("AcquisitionVoxelSize")
    if isinstance(acq_voxel, list):
        dims.extend(float(x) for x in acq_voxel)

    return max(dims) if dims else None


def select_best_fdg_pet(candidates: list[NiftiVolume]) -> NiftiVolume | None:
    """From PET candidates, pick the best FDG-PET for analysis.

    Criteria:
    - Modality == "PT"
    - AttenuationCorrectionMethod present (AC done)
    - Radiopharmaceutical contains FDG or fluorodeoxyglucose
    - Prefer static (single time-point) over dynamic
    - Prefer highest slice count
    """
    valid = []
    for vol in candidates:
        if vol.modality_tag != "PET":
            continue

        sidecar = vol.json_sidecar

        # Must be attenuation-corrected
        ac_method = sidecar.get("AttenuationCorrectionMethod", "")
        corrected_image = sidecar.get("CorrectedImage", [])
        image_type = sidecar.get("ImageType", [])
        if isinstance(image_type, list):
            image_type_str = " ".join(str(x).upper() for x in image_type)
        else:
            image_type_str = str(image_type).upper()

        has_ac = bool(ac_method) or "ATTN" in str(corrected_image).upper() or "ATTN_CORR" in image_type_str
        if not has_ac:
            continue

        # Must be FDG
        tracer = sidecar.get("Radiopharmaceutical", sidecar.get("TracerName", "")).upper()
        radiopharm_info = str(sidecar.get("RadiopharmaceuticalInformationSequence", "")).upper()
        is_fdg = "FDG" in tracer or "FLUORODEOXYGLUCOSE" in tracer or "FDG" in radiopharm_info
        if not is_fdg:
            continue

        # Check if static (prefer single time-point)
        is_static = len(vol.shape) < 4 or (len(vol.shape) == 4 and vol.shape[3] == 1)
        slice_count = vol.shape[2] if len(vol.shape) >= 3 else 0

        valid.append((vol, is_static, slice_count))

    if not valid:
        return None

    # Sort: static first, then by highest slice count
    valid.sort(key=lambda x: (not x[1], -x[2]))
    return valid[0][0]


def select_best_per_modality(all_volumes: list[NiftiVolume]) -> dict[str, NiftiVolume]:
    """Orchestrate best-volume selection per modality.

    Returns {modality: best_volume}, logs skipped with reasons.
    """
    selected: dict[str, NiftiVolume] = {}

    # Group by modality
    by_modality: dict[str, list[NiftiVolume]] = {}
    for vol in all_volumes:
        by_modality.setdefault(vol.modality_tag, []).append(vol)

    # T1 for FreeSurfer
    t1_candidates = by_modality.get("T1", [])
    best_t1 = select_best_t1_for_freesurfer(t1_candidates)
    if best_t1:
        selected["T1"] = best_t1
    elif t1_candidates:
        # Fallback: best T1 by slice count even if not meeting strict FreeSurfer criteria
        t1_candidates.sort(key=lambda v: v.shape[2] if len(v.shape) >= 3 else 0, reverse=True)
        selected["T1"] = t1_candidates[0]

    # FDG-PET
    pet_candidates = by_modality.get("PET", [])
    best_pet = select_best_fdg_pet(pet_candidates)
    if best_pet:
        selected["PET"] = best_pet

    # fMRI: pick volume with most time points and >= MIN_FMRI_VOLUMES
    fmri_candidates = by_modality.get("fMRI", [])
    valid_fmri = [
        v for v in fmri_candidates
        if len(v.shape) >= 4 and v.shape[3] >= MIN_FMRI_VOLUMES
    ]
    if valid_fmri:
        valid_fmri.sort(key=lambda v: v.shape[3], reverse=True)
        selected["fMRI"] = valid_fmri[0]

    # DTI: pick volume with bvec/bval files (dcm2niix generates them)
    dti_candidates = by_modality.get("DTI", [])
    for vol in dti_candidates:
        bvec_path = vol.nifti_path.replace(".nii.gz", ".bvec")
        if os.path.exists(bvec_path):
            selected["DTI"] = vol
            break
    else:
        if dti_candidates:
            selected["DTI"] = dti_candidates[0]

    # Other modalities: take first
    for mod in ("T2", "FLAIR", "EEG"):
        if mod in by_modality and by_modality[mod]:
            selected[mod] = by_modality[mod][0]

    return selected


async def organize_bids(
    selected: dict[str, NiftiVolume],
    subject_id: str,
    session_id: str = "01",
    output_dir: str = "/tmp/bids",
) -> str:
    """Organize selected volumes into BIDS directory structure.

    Returns the BIDS root directory path.
    """
    sub_label = f"sub-{subject_id}"
    ses_label = f"ses-{session_id}"
    bids_root = os.path.join(output_dir, sub_label, ses_label)

    modality_to_bids = {
        "T1": ("anat", f"{sub_label}_{ses_label}_T1w"),
        "T2": ("anat", f"{sub_label}_{ses_label}_T2w"),
        "FLAIR": ("anat", f"{sub_label}_{ses_label}_FLAIR"),
        "PET": ("pet", f"{sub_label}_{ses_label}_pet"),
        "fMRI": ("func", f"{sub_label}_{ses_label}_task-rest_bold"),
        "DTI": ("dwi", f"{sub_label}_{ses_label}_dwi"),
        "EEG": ("eeg", f"{sub_label}_{ses_label}_eeg"),
    }

    def _organize():
        for mod, vol in selected.items():
            if mod not in modality_to_bids:
                continue

            bids_subdir, bids_name = modality_to_bids[mod]
            target_dir = os.path.join(bids_root, bids_subdir)
            os.makedirs(target_dir, exist_ok=True)

            # Copy NIfTI
            nifti_ext = ".nii.gz" if vol.nifti_path.endswith(".nii.gz") else ".nii"
            shutil.copy2(vol.nifti_path, os.path.join(target_dir, f"{bids_name}{nifti_ext}"))

            # Copy JSON sidecar
            json_src = vol.nifti_path.replace(".nii.gz", ".json").replace(".nii", ".json")
            if os.path.exists(json_src):
                shutil.copy2(json_src, os.path.join(target_dir, f"{bids_name}.json"))

            # Copy bvec/bval for DTI
            if mod == "DTI":
                for ext in (".bvec", ".bval"):
                    src = vol.nifti_path.replace(".nii.gz", ext)
                    if os.path.exists(src):
                        shutil.copy2(src, os.path.join(target_dir, f"{bids_name}{ext}"))

    await asyncio.to_thread(_organize)
    logger.info("BIDS organized at %s for %d modalities", bids_root, len(selected))
    return bids_root


async def validate_bids(bids_dir: str) -> list[dict]:
    """Run bids-validator on a BIDS directory.

    Returns list of validation issues.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "bids-validator", bids_dir, "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()

        if stdout:
            result = json.loads(stdout.decode())
            issues = result.get("issues", {})
            errors = issues.get("errors", [])
            warnings = issues.get("warnings", [])
            return [
                {"level": "ERROR", **e} for e in errors
            ] + [
                {"level": "WARNING", **w} for w in warnings
            ]
    except FileNotFoundError:
        logger.warning("bids-validator not found, skipping validation")
    except Exception as e:
        logger.warning("bids-validator failed: %s", e)

    return []
