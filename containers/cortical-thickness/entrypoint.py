#!/usr/bin/env python3
"""NeuroHub Cortical Thickness technique container entrypoint.

Wraps FreeSurfer recon-all to extract cortical thickness and subcortical volumes.
Outputs NEUROHUB_OUTPUT JSON to stdout.

Environment:
  NEUROHUB_JOB_SPEC — base64-encoded JSON job spec (optional)
  NEUROHUB_SKIP_RECON — if "1", skip recon-all and use existing FreeSurfer output
  FREESURFER_HOME — FreeSurfer installation (default: /opt/freesurfer)
  NTHREADS — number of threads (default: 4)

Mounts:
  /input  — BIDS input directory (expects anat/T1.nii.gz or freesurfer/ dir)
  /output — output directory for results
  /opt/freesurfer — host-mounted FreeSurfer installation (read-only)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from parse_freesurfer import collect_all_features, compute_qc_score, parse_euler_number

MODULE_KEY = "Cortical_Thickness"
MODULE_VERSION = "1.0.0"


def find_t1(input_dir: Path) -> Path | None:
    """Find T1 NIfTI in input directory."""
    candidates = [
        input_dir / "anat" / "T1.nii.gz",
        input_dir / "anat" / "T1.nii",
    ]
    # Also search for any T1w file
    anat_dir = input_dir / "anat"
    if anat_dir.exists():
        for f in sorted(anat_dir.glob("*T1w*.nii*")):
            candidates.append(f)
        for f in sorted(anat_dir.glob("*T1*.nii*")):
            candidates.append(f)

    for c in candidates:
        if c.exists():
            return c
    return None


def run_recon_all(t1_path: Path, output_dir: Path, threads: int = 4) -> Path:
    """Run FreeSurfer recon-all."""
    fs_home = os.environ.get("FREESURFER_HOME", "/opt/freesurfer")
    subjects_dir = output_dir / "freesurfer_subjects"
    subjects_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["FREESURFER_HOME"] = fs_home
    env["SUBJECTS_DIR"] = str(subjects_dir)
    env["PATH"] = f"{fs_home}/bin:{env.get('PATH', '')}"

    # Source SetUpFreeSurfer.sh equivalent
    env["FSFAST_HOME"] = f"{fs_home}/fsfast"
    env["MNI_DIR"] = f"{fs_home}/mni"
    env["FSF_OUTPUT_FORMAT"] = "nii.gz"

    subject_name = "subject"
    cmd = [
        f"{fs_home}/bin/recon-all",
        "-s", subject_name,
        "-i", str(t1_path),
        "-all",
        "-threads", str(threads),
    ]

    print(f"[cortical-thickness] Running recon-all with {threads} threads...", flush=True)
    print(f"[cortical-thickness] T1 input: {t1_path}", flush=True)
    print(f"[cortical-thickness] This may take 6-12 hours.", flush=True)

    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=86400)

    if result.returncode != 0:
        print(f"[cortical-thickness] recon-all stderr: {result.stderr[-2000:]}", file=sys.stderr)
        raise RuntimeError(f"recon-all failed with exit code {result.returncode}")

    return subjects_dir / subject_name


def copy_precomputed(precomputed_dir: Path, output_dir: Path) -> Path:
    """Copy pre-computed FreeSurfer data to output."""
    dest = output_dir / "freesurfer_subjects" / "subject"
    dest.mkdir(parents=True, exist_ok=True)

    # Copy stats, mri, surf, label directories
    for subdir in ("stats", "mri", "surf", "label", "scripts"):
        src = precomputed_dir / subdir
        if src.exists():
            dst = dest / subdir
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"[cortical-thickness] Copied {subdir}/", flush=True)

    return dest


def main():
    input_dir = Path("/input")
    output_dir = Path("/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    skip_recon = os.environ.get("NEUROHUB_SKIP_RECON", "0") == "1"
    threads = int(os.environ.get("NTHREADS", "4"))

    # Check for pre-computed FreeSurfer data
    precomputed = input_dir / "freesurfer"
    if not precomputed.exists():
        precomputed = input_dir / "freesurfer_subjects" / "subject"

    if skip_recon and precomputed.exists():
        print("[cortical-thickness] Using pre-computed FreeSurfer data", flush=True)
        fs_subject_dir = copy_precomputed(precomputed, output_dir)
    else:
        t1 = find_t1(input_dir)
        if t1 is None:
            error_output = {
                "module": MODULE_KEY,
                "module_version": MODULE_VERSION,
                "qc_score": 0.0,
                "qc_flags": ["NO_T1_FOUND"],
                "features": {},
                "maps": {},
                "confidence": 0.0,
            }
            print(f"NEUROHUB_OUTPUT: {json.dumps(error_output)}", flush=True)
            sys.exit(1)

        if precomputed.exists() and (precomputed / "stats" / "aseg.stats").exists():
            print("[cortical-thickness] Pre-computed data found, skipping recon-all", flush=True)
            fs_subject_dir = copy_precomputed(precomputed, output_dir)
        else:
            fs_subject_dir = run_recon_all(t1, output_dir, threads)

    # Extract features
    print("[cortical-thickness] Extracting features from FreeSurfer stats...", flush=True)
    features = collect_all_features(fs_subject_dir)

    # Copy key output files
    maps: dict[str, str] = {}
    mri_dir = fs_subject_dir / "mri"

    for fname in ("aparc+aseg.mgz", "aparc+aseg.nii", "brain.mgz"):
        src = mri_dir / fname
        if src.exists():
            dst = output_dir / fname
            shutil.copy2(src, dst)
            maps[fname.replace(".", "_").replace("+", "_")] = str(dst)

    # Try to convert aparc+aseg to NIfTI if not already done
    aparc_nii = output_dir / "aparc_aseg.nii.gz"
    aparc_mgz = mri_dir / "aparc+aseg.mgz"
    if aparc_mgz.exists() and not aparc_nii.exists():
        fs_home = os.environ.get("FREESURFER_HOME", "/opt/freesurfer")
        mri_convert = Path(fs_home) / "bin" / "mri_convert"
        if mri_convert.exists():
            try:
                subprocess.run(
                    [str(mri_convert), str(aparc_mgz), str(aparc_nii)],
                    capture_output=True, timeout=120,
                )
                maps["aparc_aseg"] = str(aparc_nii)
            except Exception:
                pass

    # Copy thickness surfaces
    surf_dir = fs_subject_dir / "surf"
    for hemi in ("lh", "rh"):
        for suffix in ("thickness", "curv", "area"):
            src = surf_dir / f"{hemi}.{suffix}"
            if src.exists():
                dst = output_dir / f"{hemi}.{suffix}"
                shutil.copy2(src, dst)
                maps[f"{hemi}_{suffix}"] = str(dst)

    # QC
    log_file = fs_subject_dir / "scripts" / "recon-all.log"
    euler = parse_euler_number(log_file if log_file.exists() else None)
    qc_score = compute_qc_score(euler, features)

    qc_flags: list[str] = []
    if euler is not None and euler > 200:
        qc_flags.append("HIGH_EULER_NUMBER")
    if euler is not None and euler > 100:
        qc_flags.append("MODERATE_EULER_NUMBER")

    # Build output
    output = {
        "module": MODULE_KEY,
        "module_version": MODULE_VERSION,
        "qc_score": round(qc_score, 1),
        "qc_flags": qc_flags,
        "features": {k: round(v, 4) for k, v in features.items()},
        "maps": maps,
        "confidence": round(qc_score * 0.9, 1),
    }

    print(f"[cortical-thickness] Extracted {len(features)} features, QC={qc_score:.1f}", flush=True)
    print(f"NEUROHUB_OUTPUT: {json.dumps(output)}", flush=True)


if __name__ == "__main__":
    main()
