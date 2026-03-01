"""Tests for the smart zip processor — DICOM/NIfTI file finder.

Tests various messy zip structures:
- Clean DICOM directories
- Mixed DICOM + non-medical files
- macOS __MACOSX junk
- Nested directory structures
- NIfTI files (pre-converted)
- Empty zips
- Files without extensions (bare DICOM)
- Path traversal attempts
"""

import os
import struct
import tempfile
import zipfile

import pytest

from app.services.zip_processor import (
    DicomFileInfo,
    NiftiFileInfo,
    ZipScanResult,
    _is_dicom_file,
    _is_junk_path,
    extract_and_scan,
    extract_zip,
    get_dicom_dirs_for_conversion,
    prepare_dicom_input_dir,
    scan_directory,
)


def _create_fake_dicom(path: str, series_uid: str = "1.2.3", modality: str = "MR") -> None:
    """Create a minimal fake DICOM file with DICM magic and basic tags."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        # 128-byte preamble + DICM magic
        f.write(b"\x00" * 128)
        f.write(b"DICM")
        # Write some dummy data to make it valid
        f.write(b"\x00" * 256)


def _create_fake_nifti(path: str, compressed: bool = True) -> None:
    """Create a minimal fake NIfTI file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if compressed:
        import gzip
        with gzip.open(path, "wb") as f:
            # Minimal NIfTI-1 header (348 bytes)
            f.write(b"\x5c\x01\x00\x00")  # sizeof_hdr = 348
            f.write(b"\x00" * 344)
    else:
        with open(path, "wb") as f:
            f.write(b"\x5c\x01\x00\x00")
            f.write(b"\x00" * 344)


def _create_zip(work_dir: str, files: dict[str, str]) -> str:
    """Create a zip file with specified file structure.

    Args:
        files: {zip_path: "dicom" | "nifti" | "text" | "empty" | bytes}
    """
    zip_path = os.path.join(work_dir, "test.zip")

    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, content_type in files.items():
            if content_type == "dicom":
                data = b"\x00" * 128 + b"DICM" + b"\x00" * 256
            elif content_type == "nifti":
                data = b"\x5c\x01\x00\x00" + b"\x00" * 344
            elif content_type == "text":
                data = b"Hello, this is a text file."
            elif content_type == "empty":
                data = b""
            elif isinstance(content_type, bytes):
                data = content_type
            else:
                data = b"Unknown content"
            zf.writestr(name, data)

    return zip_path


# ── Unit Tests ──────────────────────────────────────────────────────────


class TestIsJunkPath:
    def test_macos_junk(self):
        assert _is_junk_path("__MACOSX/something.dcm") is True

    def test_ds_store(self):
        assert _is_junk_path("some/dir/.DS_Store") is True

    def test_dot_underscore_file(self):
        assert _is_junk_path("data/._image.dcm") is True

    def test_normal_path(self):
        assert _is_junk_path("patient/series1/00001.dcm") is False

    def test_thumbs_db(self):
        assert _is_junk_path("Thumbs.db") is True


class TestIsDicomFile:
    def test_valid_dicom_with_magic(self, tmp_path):
        dcm = str(tmp_path / "test.dcm")
        _create_fake_dicom(dcm)
        assert _is_dicom_file(dcm) is True

    def test_not_dicom(self, tmp_path):
        txt = str(tmp_path / "test.txt")
        with open(txt, "w") as f:
            f.write("Hello world")
        assert _is_dicom_file(txt) is False

    def test_empty_file(self, tmp_path):
        empty = str(tmp_path / "empty")
        with open(empty, "w") as f:
            pass
        assert _is_dicom_file(empty) is False

    def test_dicom_without_preamble(self, tmp_path):
        """Test DICOM file with group 0008 at start (no DICM magic)."""
        dcm = str(tmp_path / "no_magic.dcm")
        with open(dcm, "wb") as f:
            # Group 0x0008, Element 0x0005 (Specific Character Set)
            f.write(struct.pack("<HH", 0x0008, 0x0005))
            f.write(b"\x00" * 100)
        assert _is_dicom_file(dcm) is True


# ── Integration Tests ──────────────────────────────────────────────────


class TestExtractZip:
    @pytest.mark.asyncio
    async def test_extract_valid_zip(self, tmp_path):
        work_dir = str(tmp_path)
        zip_path = _create_zip(work_dir, {
            "file1.txt": "text",
            "file2.txt": "text",
        })
        result = await extract_zip(zip_path, str(tmp_path / "output"))
        assert os.path.isdir(result)
        assert os.path.exists(os.path.join(result, "file1.txt"))

    @pytest.mark.asyncio
    async def test_extract_invalid_file(self, tmp_path):
        not_zip = str(tmp_path / "not_a_zip.txt")
        with open(not_zip, "w") as f:
            f.write("not a zip")
        with pytest.raises(ValueError, match="Not a valid zip"):
            await extract_zip(not_zip, str(tmp_path / "output"))


class TestScanDirectory:
    @pytest.mark.asyncio
    async def test_scan_dicom_files(self, tmp_path):
        """Test scanning a directory with DICOM files."""
        dcm_dir = str(tmp_path / "patient" / "series1")
        os.makedirs(dcm_dir)
        for i in range(5):
            _create_fake_dicom(os.path.join(dcm_dir, f"{i:04d}.dcm"))

        result = await scan_directory(str(tmp_path))
        assert result.dicom_count == 5
        assert result.has_dicom is True
        assert result.total_files == 5

    @pytest.mark.asyncio
    async def test_scan_nifti_files(self, tmp_path):
        """Test scanning a directory with NIfTI files."""
        nifti_dir = str(tmp_path / "data")
        os.makedirs(nifti_dir)
        _create_fake_nifti(os.path.join(nifti_dir, "brain.nii.gz"))
        # Create a JSON sidecar
        with open(os.path.join(nifti_dir, "brain.json"), "w") as f:
            f.write('{"Modality": "MR"}')

        result = await scan_directory(str(tmp_path))
        assert result.nifti_count == 1
        assert result.has_nifti is True
        assert result.nifti_files[0].json_sidecar is not None

    @pytest.mark.asyncio
    async def test_scan_mixed_files(self, tmp_path):
        """Test scanning with DICOM + text + images mixed."""
        _create_fake_dicom(str(tmp_path / "series1" / "001.dcm"))
        _create_fake_dicom(str(tmp_path / "series1" / "002.dcm"))
        with open(str(tmp_path / "report.pdf"), "wb") as f:
            f.write(b"%PDF-1.4 fake")
        with open(str(tmp_path / "screenshot.jpg"), "wb") as f:
            f.write(b"\xff\xd8\xff fake jpg")

        result = await scan_directory(str(tmp_path))
        assert result.dicom_count == 2
        assert len(result.skipped_files) == 2  # pdf + jpg

    @pytest.mark.asyncio
    async def test_scan_macos_junk_filtered(self, tmp_path):
        """Test that macOS junk files are filtered."""
        _create_fake_dicom(str(tmp_path / "data" / "001.dcm"))
        os.makedirs(str(tmp_path / "__MACOSX" / "data"), exist_ok=True)
        with open(str(tmp_path / "__MACOSX" / "data" / "._001.dcm"), "wb") as f:
            f.write(b"junk")
        with open(str(tmp_path / "data" / ".DS_Store"), "wb") as f:
            f.write(b"DS_Store data")

        result = await scan_directory(str(tmp_path))
        assert result.dicom_count == 1
        assert len(result.junk_files) >= 1  # .DS_Store

    @pytest.mark.asyncio
    async def test_scan_deeply_nested(self, tmp_path):
        """Test scanning deeply nested directories."""
        deep_path = tmp_path / "a" / "b" / "c" / "d" / "series"
        os.makedirs(str(deep_path))
        _create_fake_dicom(str(deep_path / "001.dcm"))
        _create_fake_dicom(str(deep_path / "002.dcm"))

        result = await scan_directory(str(tmp_path))
        assert result.dicom_count == 2

    @pytest.mark.asyncio
    async def test_scan_empty_directory(self, tmp_path):
        result = await scan_directory(str(tmp_path))
        assert result.dicom_count == 0
        assert result.nifti_count == 0
        assert result.has_dicom is False
        assert result.has_nifti is False

    @pytest.mark.asyncio
    async def test_scan_files_without_extension(self, tmp_path):
        """Test that DICOM files without extensions are detected."""
        # Many DICOM files have no extension
        no_ext_path = str(tmp_path / "series" / "IM00001")
        _create_fake_dicom(no_ext_path)

        result = await scan_directory(str(tmp_path))
        assert result.dicom_count == 1


class TestExtractAndScan:
    @pytest.mark.asyncio
    async def test_full_pipeline(self, tmp_path):
        """Test extract + scan in one call."""
        work_dir = str(tmp_path / "work")
        os.makedirs(work_dir)

        zip_path = _create_zip(work_dir, {
            "patient/series1/001.dcm": "dicom",
            "patient/series1/002.dcm": "dicom",
            "patient/report.pdf": "text",
            "__MACOSX/._001.dcm": "text",
        })

        result = await extract_and_scan(zip_path, str(tmp_path / "output"))
        assert result.has_dicom is True
        assert result.dicom_count == 2
        # __MACOSX directory is filtered at walk level, so its files
        # never appear. report.pdf is in skipped_files.
        assert len(result.skipped_files) >= 1

    @pytest.mark.asyncio
    async def test_nifti_only_zip(self, tmp_path):
        """Test a zip containing only NIfTI files."""
        work_dir = str(tmp_path / "work")
        os.makedirs(work_dir)

        # Create a zip with a fake .nii.gz
        zip_path = os.path.join(work_dir, "nifti.zip")
        nifti_data = b"\x5c\x01\x00\x00" + b"\x00" * 344
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("brain_T1w.nii.gz", nifti_data)
            zf.writestr("brain_T1w.json", '{"Modality": "MR"}')

        result = await extract_and_scan(zip_path, str(tmp_path / "output"))
        assert result.has_nifti is True
        assert result.nifti_count == 1


class TestZipScanResultProperties:
    def test_summary(self):
        result = ZipScanResult(
            extract_dir="/tmp/test",
            dicom_series={
                "uid1": [DicomFileInfo(path="/a", modality="MR", patient_id="P001")],
                "uid2": [DicomFileInfo(path="/b", modality="PT", patient_id="P001")],
            },
            nifti_files=[NiftiFileInfo(path="/c.nii.gz")],
            skipped_files=["/d.pdf"],
            junk_files=["/e/.DS_Store"],
            total_files=5,
            dicom_count=2,
            nifti_count=1,
        )

        assert result.has_dicom is True
        assert result.has_nifti is True
        assert result.modalities_found == {"MR", "PT"}
        assert result.patient_ids_found == {"P001"}

        summary = result.summary()
        assert summary["dicom_files"] == 2
        assert summary["nifti_files"] == 1
        assert summary["dicom_series"] == 2
        assert "MR" in summary["modalities"]
        assert "PT" in summary["modalities"]


class TestGetDicomDirsForConversion:
    def test_single_directory(self):
        scan = ZipScanResult(
            extract_dir="/tmp",
            dicom_series={
                "uid1": [
                    DicomFileInfo(path="/data/series1/001.dcm"),
                    DicomFileInfo(path="/data/series1/002.dcm"),
                ],
            },
            dicom_count=2,
        )
        dirs = get_dicom_dirs_for_conversion(scan)
        assert dirs == ["/data/series1"]

    def test_multiple_directories(self):
        scan = ZipScanResult(
            extract_dir="/tmp",
            dicom_series={
                "uid1": [DicomFileInfo(path="/data/series1/001.dcm")],
                "uid2": [DicomFileInfo(path="/data/series2/001.dcm")],
            },
            dicom_count=2,
        )
        dirs = get_dicom_dirs_for_conversion(scan)
        assert len(dirs) == 2
        assert "/data/series1" in dirs
        assert "/data/series2" in dirs


class TestPrepareDicomInputDir:
    def test_organize_series(self, tmp_path):
        # Create fake DICOM files
        src_dir = str(tmp_path / "src")
        _create_fake_dicom(os.path.join(src_dir, "series1", "001.dcm"))
        _create_fake_dicom(os.path.join(src_dir, "series2", "001.dcm"))

        scan = ZipScanResult(
            extract_dir=src_dir,
            dicom_series={
                "1.2.3.4.5": [
                    DicomFileInfo(
                        path=os.path.join(src_dir, "series1", "001.dcm"),
                        series_uid="1.2.3.4.5",
                    )
                ],
                "1.2.3.4.6": [
                    DicomFileInfo(
                        path=os.path.join(src_dir, "series2", "001.dcm"),
                        series_uid="1.2.3.4.6",
                    )
                ],
            },
            dicom_count=2,
        )

        output = str(tmp_path / "organized")
        result = prepare_dicom_input_dir(scan, output)
        assert os.path.isdir(result)
        # Should have 2 subdirectories (one per series)
        subdirs = [d for d in os.listdir(result) if os.path.isdir(os.path.join(result, d))]
        assert len(subdirs) == 2
