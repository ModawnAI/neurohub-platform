"""Smart ZIP processor — extracts and classifies medical imaging files.

Handles messy zip structures where DICOM files may be:
- Mixed with non-medical files (PDFs, screenshots, reports)
- In deeply nested directories
- Without file extensions (bare DICOM files)
- Mixed with macOS artifacts (__MACOSX, .DS_Store)
- Already converted to NIfTI format
- Organized by series or randomly dumped
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import struct
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Files/dirs to always ignore
JUNK_NAMES = {
    "__MACOSX",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".Spotlight-V100",
    ".Trashes",
    ".fseventsd",
    ".TemporaryItems",
}

# File extensions that are definitely NOT medical imaging
NON_MEDICAL_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".rtf", ".csv", ".log",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg",
    ".mp4", ".avi", ".mov", ".mp3", ".wav",
    ".py", ".js", ".html", ".css", ".xml", ".yaml", ".yml",
    ".exe", ".dll", ".app", ".sh", ".bat",
    ".zip", ".tar", ".gz", ".rar", ".7z",
}

# NIfTI file patterns
NIFTI_EXTENSIONS = {".nii", ".nii.gz"}


@dataclass
class DicomFileInfo:
    """Information about a discovered DICOM file."""

    path: str
    series_uid: str = ""
    series_description: str = ""
    modality: str = ""
    patient_id: str = ""
    study_uid: str = ""
    instance_number: int = 0
    file_size: int = 0


@dataclass
class NiftiFileInfo:
    """Information about a discovered NIfTI file."""

    path: str
    json_sidecar: str | None = None
    bvec_path: str | None = None
    bval_path: str | None = None
    file_size: int = 0


@dataclass
class ZipScanResult:
    """Result of scanning an extracted zip archive."""

    extract_dir: str
    dicom_series: dict[str, list[DicomFileInfo]] = field(default_factory=dict)
    nifti_files: list[NiftiFileInfo] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    junk_files: list[str] = field(default_factory=list)
    total_files: int = 0
    dicom_count: int = 0
    nifti_count: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def has_dicom(self) -> bool:
        return self.dicom_count > 0

    @property
    def has_nifti(self) -> bool:
        return self.nifti_count > 0

    @property
    def modalities_found(self) -> set[str]:
        mods = set()
        for files in self.dicom_series.values():
            if files and files[0].modality:
                mods.add(files[0].modality)
        return mods

    @property
    def patient_ids_found(self) -> set[str]:
        pids = set()
        for files in self.dicom_series.values():
            for f in files:
                if f.patient_id:
                    pids.add(f.patient_id)
        return pids

    def summary(self) -> dict:
        return {
            "total_files": self.total_files,
            "dicom_files": self.dicom_count,
            "dicom_series": len(self.dicom_series),
            "nifti_files": self.nifti_count,
            "skipped_files": len(self.skipped_files),
            "junk_files": len(self.junk_files),
            "modalities": sorted(self.modalities_found),
            "patient_ids": sorted(self.patient_ids_found),
            "errors": self.errors[:10],
        }


def _is_junk_path(path: str) -> bool:
    """Check if a file path contains junk directories or filenames."""
    parts = Path(path).parts
    for part in parts:
        if part in JUNK_NAMES or part.startswith("._"):
            return True
    return False


def _is_dicom_file(filepath: str) -> bool:
    """Check if a file is DICOM by reading magic bytes.

    DICOM files have "DICM" at offset 128. However, some older DICOM files
    lack the preamble, so we also check for common DICOM tags at the start.
    """
    try:
        with open(filepath, "rb") as f:
            # Check DICM magic at offset 128
            f.seek(128)
            magic = f.read(4)
            if magic == b"DICM":
                return True

            # Fallback: check for DICOM group/element tags at start
            # Common first tags: (0002,0000), (0002,0001), (0008,0005), (0008,0008)
            f.seek(0)
            header = f.read(8)
            if len(header) < 8:
                return False

            # Check for group 0002 or 0008 at byte 0 (little-endian)
            group = struct.unpack("<H", header[0:2])[0]
            if group in (0x0002, 0x0008):
                return True

            return False
    except (OSError, struct.error):
        return False


def _read_dicom_tags(filepath: str) -> DicomFileInfo | None:
    """Read key DICOM tags using pydicom (lightweight read)."""
    try:
        import pydicom

        ds = pydicom.dcmread(filepath, stop_before_pixels=True, force=True)

        return DicomFileInfo(
            path=filepath,
            series_uid=str(getattr(ds, "SeriesInstanceUID", "")),
            series_description=str(getattr(ds, "SeriesDescription", "")),
            modality=str(getattr(ds, "Modality", "")),
            patient_id=str(getattr(ds, "PatientID", "")),
            study_uid=str(getattr(ds, "StudyInstanceUID", "")),
            instance_number=int(getattr(ds, "InstanceNumber", 0) or 0),
            file_size=os.path.getsize(filepath),
        )
    except Exception as e:
        logger.debug("Failed to read DICOM tags from %s: %s", filepath, e)
        return None


def _find_nifti_companions(nifti_path: str) -> NiftiFileInfo:
    """Find JSON sidecar, bvec, bval files that accompany a NIfTI file."""
    base = nifti_path
    if base.endswith(".nii.gz"):
        base = base[:-7]
    elif base.endswith(".nii"):
        base = base[:-4]

    info = NiftiFileInfo(
        path=nifti_path,
        file_size=os.path.getsize(nifti_path),
    )

    json_path = base + ".json"
    if os.path.exists(json_path):
        info.json_sidecar = json_path

    bvec_path = base + ".bvec"
    if os.path.exists(bvec_path):
        info.bvec_path = bvec_path

    bval_path = base + ".bval"
    if os.path.exists(bval_path):
        info.bval_path = bval_path

    return info


async def extract_zip(zip_path: str, output_dir: str) -> str:
    """Extract a zip file safely (prevents zip-bomb and path traversal).

    Returns the extraction directory path.
    """
    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"Not a valid zip file: {zip_path}")

    extract_dir = os.path.join(output_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)

    def _safe_extract():
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Check for path traversal
            for info in zf.infolist():
                member_path = os.path.realpath(os.path.join(extract_dir, info.filename))
                if not member_path.startswith(os.path.realpath(extract_dir)):
                    raise ValueError(
                        f"Zip contains path traversal: {info.filename}"
                    )

            # Check total uncompressed size (max 50GB)
            total_size = sum(i.file_size for i in zf.infolist())
            max_size = 50 * 1024 * 1024 * 1024  # 50GB
            if total_size > max_size:
                raise ValueError(
                    f"Zip uncompressed size ({total_size / 1e9:.1f}GB) exceeds "
                    f"maximum ({max_size / 1e9:.0f}GB)"
                )

            zf.extractall(extract_dir)

    await asyncio.to_thread(_safe_extract)
    logger.info("Extracted %s to %s", zip_path, extract_dir)
    return extract_dir


async def scan_directory(directory: str) -> ZipScanResult:
    """Scan an extracted directory for DICOM and NIfTI files.

    Walks the entire directory tree, identifies medical imaging files,
    groups DICOMs by series, and collects NIfTI files with companions.
    """
    result = ZipScanResult(extract_dir=directory)

    def _scan():
        dicom_files: dict[str, list[DicomFileInfo]] = defaultdict(list)
        nifti_files: list[NiftiFileInfo] = []

        for root, dirs, files in os.walk(directory):
            # Skip junk directories
            dirs[:] = [d for d in dirs if d not in JUNK_NAMES and not d.startswith("._")]

            for fname in files:
                filepath = os.path.join(root, fname)
                result.total_files += 1

                # Skip junk files
                if _is_junk_path(filepath):
                    result.junk_files.append(filepath)
                    continue

                # Skip empty files
                try:
                    if os.path.getsize(filepath) == 0:
                        result.skipped_files.append(filepath)
                        continue
                except OSError:
                    continue

                ext = ""
                fname_lower = fname.lower()
                if fname_lower.endswith(".nii.gz"):
                    ext = ".nii.gz"
                else:
                    ext = os.path.splitext(fname_lower)[1]

                # Check for NIfTI files
                if ext in NIFTI_EXTENSIONS:
                    info = _find_nifti_companions(filepath)
                    nifti_files.append(info)
                    result.nifti_count += 1
                    continue

                # Skip known non-medical files
                if ext in NON_MEDICAL_EXTENSIONS:
                    result.skipped_files.append(filepath)
                    continue

                # Check if it's a DICOM file (by magic bytes)
                if _is_dicom_file(filepath):
                    info = _read_dicom_tags(filepath)
                    if info:
                        series_key = info.series_uid or f"unknown_series_{id(info)}"
                        dicom_files[series_key].append(info)
                        result.dicom_count += 1
                    else:
                        # Valid DICOM magic but couldn't read tags
                        dicom_files["__unreadable__"].append(
                            DicomFileInfo(
                                path=filepath,
                                file_size=os.path.getsize(filepath),
                            )
                        )
                        result.dicom_count += 1
                else:
                    result.skipped_files.append(filepath)

        # Sort DICOM files within each series by instance number
        for series_uid, files_list in dicom_files.items():
            files_list.sort(key=lambda x: x.instance_number)

        result.dicom_series = dict(dicom_files)
        result.nifti_files = nifti_files

    await asyncio.to_thread(_scan)

    logger.info(
        "Scan complete: %d total files, %d DICOM (%d series), %d NIfTI, "
        "%d skipped, %d junk",
        result.total_files,
        result.dicom_count,
        len(result.dicom_series),
        result.nifti_count,
        len(result.skipped_files),
        len(result.junk_files),
    )
    return result


async def extract_and_scan(zip_path: str, work_dir: str) -> ZipScanResult:
    """Full pipeline: extract zip → scan for medical imaging files.

    This is the main entry point for the zip processor.
    """
    extract_dir = await extract_zip(zip_path, work_dir)
    result = await scan_directory(extract_dir)
    return result


def get_dicom_dirs_for_conversion(scan_result: ZipScanResult) -> list[str]:
    """Get unique directories containing DICOM files for dcm2niix conversion.

    dcm2niix works on directories, so we need to find the parent directories
    of each DICOM series. If multiple series share a directory, dcm2niix
    handles them correctly.

    Returns deduplicated list of directories sorted by path.
    """
    dicom_dirs: set[str] = set()

    for series_files in scan_result.dicom_series.values():
        for f in series_files:
            dicom_dirs.add(os.path.dirname(f.path))

    return sorted(dicom_dirs)


def prepare_dicom_input_dir(
    scan_result: ZipScanResult,
    output_dir: str,
) -> str:
    """Collect all DICOM files into a flat structure suitable for dcm2niix.

    When DICOM files are scattered across many nested directories, dcm2niix
    may miss some. This function copies (or symlinks) all found DICOMs into
    a single directory organized by series.

    Returns path to the organized DICOM directory.
    """
    organized_dir = os.path.join(output_dir, "dicom_organized")
    os.makedirs(organized_dir, exist_ok=True)

    for series_uid, files in scan_result.dicom_series.items():
        # Create a subdirectory per series
        safe_uid = series_uid.replace(".", "_")[:64]
        series_dir = os.path.join(organized_dir, safe_uid)
        os.makedirs(series_dir, exist_ok=True)

        for f in files:
            dst = os.path.join(series_dir, os.path.basename(f.path))
            # Use symlink if same filesystem, copy otherwise
            if not os.path.exists(dst):
                try:
                    os.symlink(f.path, dst)
                except OSError:
                    shutil.copy2(f.path, dst)

    logger.info(
        "Organized %d DICOM series into %s",
        len(scan_result.dicom_series),
        organized_dir,
    )
    return organized_dir
