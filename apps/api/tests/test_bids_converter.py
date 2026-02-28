"""Phase 8 — BIDS converter unit tests (no external tools needed)."""

import os
import tempfile
import zipfile

import pytest

from app.services.bids_converter import (
    MIN_VOLUME_SLICES,
    NiftiVolume,
    classify_modality,
    decompress_upload,
    filter_by_slice_count,
    organize_bids,
    select_best_fdg_pet,
    select_best_per_modality,
    select_best_t1_for_freesurfer,
)

pytestmark = pytest.mark.anyio


# --- classify_modality ---


def test_classify_modality_from_sidecar_t1():
    sidecar = {"Modality": "MR", "SeriesDescription": "T1_MPRAGE_SAG", "MRAcquisitionType": "3D"}
    assert classify_modality(sidecar) == "T1"


def test_classify_modality_from_sidecar_pet():
    sidecar = {"Modality": "PT", "SeriesDescription": "FDG_WB"}
    assert classify_modality(sidecar) == "PET"


def test_classify_modality_fmri():
    sidecar = {"Modality": "MR", "SeriesDescription": "BOLD_resting", "RepetitionTime": 2.0}
    assert classify_modality(sidecar) == "fMRI"


def test_classify_modality_dti():
    sidecar = {"Modality": "MR", "SeriesDescription": "DTI_64dir"}
    assert classify_modality(sidecar) == "DTI"


def test_classify_modality_flair():
    sidecar = {"Modality": "MR", "SeriesDescription": "FLAIR_AX"}
    assert classify_modality(sidecar) == "FLAIR"


# --- filter_by_slice_count ---


def test_filter_rejects_low_slice_localizer():
    vol = NiftiVolume(
        nifti_path="/tmp/scout.nii.gz",
        json_sidecar={},
        shape=(256, 256, 20),
        modality_tag="T1",
    )
    valid, skipped = filter_by_slice_count([vol])
    assert len(valid) == 0
    assert len(skipped) == 1
    assert "SKIPPED_LOW_SLICES" in skipped[0].skip_reason


def test_filter_accepts_valid_volume():
    vol = NiftiVolume(
        nifti_path="/tmp/t1.nii.gz",
        json_sidecar={},
        shape=(256, 256, 160),
        modality_tag="T1",
    )
    valid, skipped = filter_by_slice_count([vol])
    assert len(valid) == 1
    assert len(skipped) == 0


def test_filter_rejects_2d():
    vol = NiftiVolume(
        nifti_path="/tmp/flat.nii.gz",
        json_sidecar={},
        shape=(256, 256),
        modality_tag="T1",
    )
    valid, skipped = filter_by_slice_count([vol])
    assert len(valid) == 0
    assert "NOT_3D" in skipped[0].skip_reason


# --- select_best_t1_for_freesurfer ---


def test_select_t1_prefers_3d_mprage():
    vol_3d = NiftiVolume(
        nifti_path="/tmp/t1_3d.nii.gz",
        json_sidecar={
            "MRAcquisitionType": "3D",
            "SeriesDescription": "MPRAGE",
            "SliceThickness": 1.0,
            "PixelSpacing": [1.0, 1.0],
        },
        shape=(256, 256, 176),
        modality_tag="T1",
    )
    vol_2d = NiftiVolume(
        nifti_path="/tmp/t1_2d.nii.gz",
        json_sidecar={
            "MRAcquisitionType": "2D",
            "SeriesDescription": "T1_AX",
            "SliceThickness": 5.0,
        },
        shape=(256, 256, 30),
        modality_tag="T1",
    )
    result = select_best_t1_for_freesurfer([vol_3d, vol_2d])
    assert result is not None
    assert result.nifti_path == "/tmp/t1_3d.nii.gz"


def test_select_t1_prefers_highest_resolution():
    vol_09mm = NiftiVolume(
        nifti_path="/tmp/t1_09.nii.gz",
        json_sidecar={
            "MRAcquisitionType": "3D",
            "SeriesDescription": "MPRAGE",
            "SliceThickness": 0.9,
            "PixelSpacing": [0.9, 0.9],
        },
        shape=(256, 256, 192),
        modality_tag="T1",
    )
    vol_12mm = NiftiVolume(
        nifti_path="/tmp/t1_12.nii.gz",
        json_sidecar={
            "MRAcquisitionType": "3D",
            "SeriesDescription": "MPRAGE",
            "SliceThickness": 1.2,
            "PixelSpacing": [1.2, 1.2],
        },
        shape=(256, 256, 160),
        modality_tag="T1",
    )
    result = select_best_t1_for_freesurfer([vol_12mm, vol_09mm])
    assert result.nifti_path == "/tmp/t1_09.nii.gz"


def test_select_t1_rejects_no_candidates():
    # 2D only, no valid 3D
    vol = NiftiVolume(
        nifti_path="/tmp/t1_bad.nii.gz",
        json_sidecar={"MRAcquisitionType": "2D"},
        shape=(256, 256, 30),
        modality_tag="T1",
    )
    assert select_best_t1_for_freesurfer([vol]) is None


def test_select_t1_rejects_coarse_voxel():
    vol = NiftiVolume(
        nifti_path="/tmp/t1_coarse.nii.gz",
        json_sidecar={
            "MRAcquisitionType": "3D",
            "SeriesDescription": "MPRAGE",
            "SliceThickness": 2.0,
            "PixelSpacing": [1.0, 1.0],
        },
        shape=(256, 256, 176),
        modality_tag="T1",
    )
    assert select_best_t1_for_freesurfer([vol]) is None


# --- select_best_fdg_pet ---


def test_select_pet_prefers_ac_over_nac():
    vol_ac = NiftiVolume(
        nifti_path="/tmp/pet_ac.nii.gz",
        json_sidecar={
            "Modality": "PT",
            "AttenuationCorrectionMethod": "CT",
            "Radiopharmaceutical": "FDG",
        },
        shape=(128, 128, 89),
        modality_tag="PET",
    )
    vol_nac = NiftiVolume(
        nifti_path="/tmp/pet_nac.nii.gz",
        json_sidecar={
            "Modality": "PT",
            "Radiopharmaceutical": "FDG",
        },
        shape=(128, 128, 89),
        modality_tag="PET",
    )
    result = select_best_fdg_pet([vol_nac, vol_ac])
    assert result is not None
    assert result.nifti_path == "/tmp/pet_ac.nii.gz"


def test_select_pet_requires_fdg_tracer():
    vol_amyloid = NiftiVolume(
        nifti_path="/tmp/pet_amyloid.nii.gz",
        json_sidecar={
            "Modality": "PT",
            "AttenuationCorrectionMethod": "CT",
            "Radiopharmaceutical": "Florbetapir",
        },
        shape=(128, 128, 89),
        modality_tag="PET",
    )
    assert select_best_fdg_pet([vol_amyloid]) is None


def test_select_pet_prefers_static_over_dynamic():
    vol_static = NiftiVolume(
        nifti_path="/tmp/pet_static.nii.gz",
        json_sidecar={
            "Modality": "PT",
            "AttenuationCorrectionMethod": "CT",
            "Radiopharmaceutical": "FDG",
        },
        shape=(128, 128, 89),
        modality_tag="PET",
    )
    vol_dynamic = NiftiVolume(
        nifti_path="/tmp/pet_dynamic.nii.gz",
        json_sidecar={
            "Modality": "PT",
            "AttenuationCorrectionMethod": "CT",
            "Radiopharmaceutical": "FDG",
        },
        shape=(128, 128, 89, 20),
        modality_tag="PET",
    )
    result = select_best_fdg_pet([vol_dynamic, vol_static])
    assert result.nifti_path == "/tmp/pet_static.nii.gz"


def test_select_pet_prefers_axial_high_slices():
    vol_low = NiftiVolume(
        nifti_path="/tmp/pet_low.nii.gz",
        json_sidecar={
            "Modality": "PT",
            "AttenuationCorrectionMethod": "CT",
            "Radiopharmaceutical": "FDG",
        },
        shape=(128, 128, 50),
        modality_tag="PET",
    )
    vol_high = NiftiVolume(
        nifti_path="/tmp/pet_high.nii.gz",
        json_sidecar={
            "Modality": "PT",
            "AttenuationCorrectionMethod": "CT",
            "Radiopharmaceutical": "FDG",
        },
        shape=(128, 128, 201),
        modality_tag="PET",
    )
    result = select_best_fdg_pet([vol_low, vol_high])
    assert result.nifti_path == "/tmp/pet_high.nii.gz"


# --- decompress_upload ---


async def test_decompress_zip_upload():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test zip
        zip_path = os.path.join(tmpdir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test_file.dcm", b"fake dicom data")
            zf.writestr("subdir/another.dcm", b"more data")

        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(output_dir)
        extracted = await decompress_upload(zip_path, output_dir)

        assert os.path.isdir(extracted)
        assert os.path.exists(os.path.join(extracted, "test_file.dcm"))
        assert os.path.exists(os.path.join(extracted, "subdir", "another.dcm"))


# --- organize_bids ---


async def test_bids_directory_structure_correct():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create fake NIfTI files
        nifti_path = os.path.join(tmpdir, "t1.nii.gz")
        json_path = os.path.join(tmpdir, "t1.json")
        with open(nifti_path, "wb") as f:
            f.write(b"fake nifti")
        with open(json_path, "w") as f:
            f.write("{}")

        selected = {
            "T1": NiftiVolume(
                nifti_path=nifti_path,
                json_sidecar={},
                shape=(256, 256, 176),
                modality_tag="T1",
            )
        }

        bids_root = await organize_bids(selected, subject_id="001", output_dir=tmpdir)
        expected_t1 = os.path.join(bids_root, "anat", "sub-001_ses-01_T1w.nii.gz")
        assert os.path.exists(expected_t1)


# --- mixed folder sorting ---


def test_mixed_folder_sorted_by_modality():
    volumes = [
        NiftiVolume("/tmp/a.nii.gz", {"Modality": "MR", "SeriesDescription": "T1_MPRAGE", "MRAcquisitionType": "3D"}, (256, 256, 176), ""),
        NiftiVolume("/tmp/b.nii.gz", {"Modality": "PT", "SeriesDescription": "FDG_WB"}, (128, 128, 89), ""),
        NiftiVolume("/tmp/c.nii.gz", {"Modality": "MR", "SeriesDescription": "BOLD_rest", "RepetitionTime": 2.0}, (64, 64, 40, 200), ""),
    ]
    # Reclassify
    for vol in volumes:
        vol.modality_tag = classify_modality(vol.json_sidecar)

    modalities = {vol.modality_tag for vol in volumes}
    assert "T1" in modalities
    assert "PET" in modalities
    assert "fMRI" in modalities
    assert len(modalities) == 3


# --- Acquisition Suitability Selector: skip unsuitable series ---


def test_select_per_modality_skips_unsuitable_fmri():
    """fMRI with < 100 time points is skipped by select_best_per_modality."""
    volumes = [
        NiftiVolume("/tmp/fmri_short.nii.gz", {"RepetitionTime": 2.0}, (64, 64, 40, 50), "fMRI"),
    ]
    selected = select_best_per_modality(volumes)
    assert "fMRI" not in selected


def test_select_per_modality_picks_fmri_with_enough_volumes():
    """fMRI with >= 100 time points is selected."""
    volumes = [
        NiftiVolume("/tmp/fmri_good.nii.gz", {"RepetitionTime": 2.0}, (64, 64, 40, 200), "fMRI"),
    ]
    selected = select_best_per_modality(volumes)
    assert "fMRI" in selected


def test_select_per_modality_t1_fallback_when_no_strict_match():
    """When no T1 meets strict FreeSurfer criteria, fallback picks highest slice count."""
    volumes = [
        NiftiVolume("/tmp/t1_2d.nii.gz", {
            "MRAcquisitionType": "2D",
            "SeriesDescription": "T1_AX",
            "SliceThickness": 5.0,
        }, (256, 256, 120), "T1"),
    ]
    selected = select_best_per_modality(volumes)
    # Fallback picks the 2D T1 since it's the only one
    assert "T1" in selected
    assert selected["T1"].nifti_path == "/tmp/t1_2d.nii.gz"


def test_select_per_modality_dti_requires_bvec():
    """DTI selection prefers volumes with bvec files, falls back to first."""
    # No bvec file exists for this path
    volumes = [
        NiftiVolume("/tmp/dti_no_bvec.nii.gz", {}, (128, 128, 70, 64), "DTI"),
    ]
    selected = select_best_per_modality(volumes)
    # Should still select (fallback), but bvec won't exist
    assert "DTI" in selected


def test_skip_reason_set_for_low_slices():
    """Volumes below MIN_VOLUME_SLICES get skip_reason with slice count info."""
    vol = NiftiVolume("/tmp/scout.nii.gz", {}, (256, 256, 15), "T1")
    _, skipped = filter_by_slice_count([vol])
    assert len(skipped) == 1
    assert "15" in skipped[0].skip_reason
    assert "SKIPPED_LOW_SLICES" in skipped[0].skip_reason
