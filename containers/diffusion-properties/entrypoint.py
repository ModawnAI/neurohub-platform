#!/usr/bin/env python3
"""NeuroHub Diffusion Properties technique container entrypoint.

Wraps FSL eddy + MRtrix3 dwi2tensor to extract FA/MD/RD/AD metrics.
Outputs NEUROHUB_OUTPUT JSON to stdout.

Mounts:
  /input  — BIDS input (expects dwi/*.nii.gz + .bvec + .bval, anat/T1.nii.gz)
  /output — output directory
  /opt/fsl — host-mounted FSL (read-only)
  /opt/mrtrix3 — host-mounted MRtrix3 (read-only)
  /opt/freesurfer — host-mounted FreeSurfer (for mri_convert, optional)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

MODULE_KEY = "Diffusion_Properties"
MODULE_VERSION = "1.0.0"


def setup_env() -> dict[str, str]:
    """Set up PATH with host-mounted tools."""
    env = os.environ.copy()
    fsl_dir = os.environ.get("FSLDIR", "/opt/fsl")
    mrtrix_dir = os.environ.get("MRTRIX_DIR", "/opt/mrtrix3")
    fs_home = os.environ.get("FREESURFER_HOME", "/opt/freesurfer")

    env["FSLDIR"] = fsl_dir
    env["FSLOUTPUTTYPE"] = "NIFTI_GZ"
    env["PATH"] = f"{mrtrix_dir}/bin:{fsl_dir}/bin:{fsl_dir}/share/fsl/bin:{fs_home}/bin:{env.get('PATH', '')}"

    # FSL setup
    fsl_conf = Path(fsl_dir) / "etc" / "fslconf" / "fsl.sh"
    if fsl_conf.exists():
        env["FSLDIR"] = fsl_dir

    return env


def find_dwi(input_dir: Path) -> tuple[Path, Path, Path] | None:
    """Find DWI NIfTI + bvec + bval files."""
    dwi_dir = input_dir / "dwi"
    if not dwi_dir.exists():
        dwi_dir = input_dir

    for nii in sorted(dwi_dir.glob("*.nii.gz")):
        base = nii.name.replace(".nii.gz", "")
        bvec = nii.parent / f"{base}.bvec"
        bval = nii.parent / f"{base}.bval"
        if bvec.exists() and bval.exists():
            return nii, bvec, bval

    # Try case-insensitive
    for nii in sorted(dwi_dir.glob("*[Dd][Ww][Ii]*.nii.gz")):
        base = nii.name.replace(".nii.gz", "")
        bvec = nii.parent / f"{base}.bvec"
        bval = nii.parent / f"{base}.bval"
        if bvec.exists() and bval.exists():
            return nii, bvec, bval

    return None


def run_cmd(cmd: list[str], env: dict, desc: str, timeout: int = 3600) -> subprocess.CompletedProcess:
    """Run command with logging."""
    print(f"[diffusion-properties] {desc}...", flush=True)
    print(f"[diffusion-properties] CMD: {' '.join(cmd[:5])}...", flush=True)
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        print(f"[diffusion-properties] STDERR: {result.stderr[-1000:]}", file=sys.stderr, flush=True)
        raise RuntimeError(f"{desc} failed (exit {result.returncode})")
    return result


def compute_mean_from_mask(nii_path: Path, mask_path: Path | None, env: dict) -> float | None:
    """Compute mean value within a mask using fslstats."""
    try:
        if mask_path and mask_path.exists():
            result = subprocess.run(
                ["fslstats", str(nii_path), "-k", str(mask_path), "-M"],
                env=env, capture_output=True, text=True, timeout=60,
            )
        else:
            result = subprocess.run(
                ["fslstats", str(nii_path), "-M"],
                env=env, capture_output=True, text=True, timeout=60,
            )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    return None


def main():
    input_dir = Path("/input")
    output_dir = Path("/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    env = setup_env()
    work_dir = output_dir / "work"
    work_dir.mkdir(exist_ok=True)

    # Find DWI data
    dwi_result = find_dwi(input_dir)
    if dwi_result is None:
        output = {
            "module": MODULE_KEY,
            "module_version": MODULE_VERSION,
            "qc_score": 0.0,
            "qc_flags": ["NO_DWI_FOUND"],
            "features": {},
            "maps": {},
            "confidence": 0.0,
        }
        print(f"NEUROHUB_OUTPUT: {json.dumps(output)}", flush=True)
        sys.exit(1)

    dwi_nii, bvec, bval = dwi_result
    print(f"[diffusion-properties] DWI: {dwi_nii.name}", flush=True)

    # Step 1: Convert to MRtrix format
    dwi_mif = work_dir / "dwi.mif"
    run_cmd(
        ["mrconvert", str(dwi_nii), str(dwi_mif),
         "-fslgrad", str(bvec), str(bval), "-force"],
        env, "Converting DWI to MIF"
    )

    # Step 2: Denoise
    dwi_denoised = work_dir / "dwi_denoised.mif"
    try:
        run_cmd(
            ["dwidenoise", str(dwi_mif), str(dwi_denoised), "-force"],
            env, "Denoising DWI"
        )
    except RuntimeError:
        print("[diffusion-properties] Denoising failed, continuing with original", flush=True)
        dwi_denoised = dwi_mif

    # Step 3: Extract b0 and create brain mask
    b0 = work_dir / "b0.mif"
    mask = work_dir / "mask.mif"
    run_cmd(
        ["dwiextract", str(dwi_denoised), str(b0), "-bzero", "-force"],
        env, "Extracting b0 volume"
    )
    # Average b0 volumes
    b0_mean = work_dir / "b0_mean.mif"
    run_cmd(
        ["mrmath", str(b0), "mean", str(b0_mean), "-axis", "3", "-force"],
        env, "Averaging b0 volumes"
    )
    run_cmd(
        ["dwi2mask", str(dwi_denoised), str(mask), "-force"],
        env, "Creating brain mask"
    )

    # Step 4: Fit diffusion tensor
    tensor = work_dir / "tensor.mif"
    run_cmd(
        ["dwi2tensor", str(dwi_denoised), str(tensor), "-mask", str(mask), "-force"],
        env, "Fitting diffusion tensor"
    )

    # Step 5: Extract scalar maps
    fa_map = output_dir / "fa.nii.gz"
    md_map = output_dir / "md.nii.gz"
    ad_map = output_dir / "ad.nii.gz"
    rd_map = output_dir / "rd.nii.gz"
    colorfa_map = output_dir / "colorfa.mif"

    run_cmd(
        ["tensor2metric", str(tensor),
         "-fa", str(fa_map),
         "-adc", str(md_map),
         "-ad", str(ad_map),
         "-rd", str(rd_map),
         "-force"],
        env, "Extracting FA/MD/AD/RD maps"
    )

    # Color FA (for visualization)
    try:
        run_cmd(
            ["tensor2metric", str(tensor), "-vector", str(colorfa_map), "-force"],
            env, "Generating color FA"
        )
    except RuntimeError:
        print("[diffusion-properties] Color FA generation failed, skipping", flush=True)

    # Convert mask to NIfTI for fslstats
    mask_nii = work_dir / "mask.nii.gz"
    run_cmd(
        ["mrconvert", str(mask), str(mask_nii), "-force"],
        env, "Converting mask to NIfTI"
    )

    # Step 6: Extract mean values
    features: dict[str, float] = {}

    for name, path in [("fa", fa_map), ("md", md_map), ("ad", ad_map), ("rd", rd_map)]:
        val = compute_mean_from_mask(path, mask_nii, env)
        if val is not None:
            features[f"mean_{name}"] = round(val, 6)

    # Compute SNR from b0
    try:
        result = subprocess.run(
            ["fslstats", str(work_dir / "b0_mean.nii.gz"
                if (work_dir / "b0_mean.nii.gz").exists()
                else str(b0_mean)), "-k", str(mask_nii), "-M", "-S"],
            env=env, capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) >= 2:
                mean_sig = float(parts[0])
                std_sig = float(parts[1])
                if std_sig > 0:
                    features["b0_snr"] = round(mean_sig / std_sig, 2)
    except Exception:
        pass

    # Convert b0_mean for mask stats
    b0_mean_nii = work_dir / "b0_mean.nii.gz"
    if not b0_mean_nii.exists():
        try:
            run_cmd(
                ["mrconvert", str(b0_mean), str(b0_mean_nii), "-force"],
                env, "Converting b0 mean to NIfTI"
            )
        except RuntimeError:
            pass

    # QC score
    qc_flags: list[str] = []
    qc_score = 85.0

    mean_fa = features.get("mean_fa")
    if mean_fa is not None:
        if 0.3 <= mean_fa <= 0.55:
            qc_score = 90.0
        elif 0.2 <= mean_fa <= 0.65:
            qc_score = 70.0
            qc_flags.append("FA_OUTSIDE_NORMAL_RANGE")
        else:
            qc_score = 40.0
            qc_flags.append("FA_ABNORMAL")

    snr = features.get("b0_snr")
    if snr is not None and snr < 10:
        qc_score = min(qc_score, 50.0)
        qc_flags.append("LOW_SNR")

    maps = {
        "fa_map": str(fa_map),
        "md_map": str(md_map),
        "ad_map": str(ad_map),
        "rd_map": str(rd_map),
    }
    if colorfa_map.exists():
        maps["colorfa"] = str(colorfa_map)

    output = {
        "module": MODULE_KEY,
        "module_version": MODULE_VERSION,
        "qc_score": round(qc_score, 1),
        "qc_flags": qc_flags,
        "features": features,
        "maps": maps,
        "confidence": round(qc_score * 0.85, 1),
    }

    print(f"[diffusion-properties] Extracted {len(features)} features, QC={qc_score:.1f}", flush=True)
    print(f"NEUROHUB_OUTPUT: {json.dumps(output)}", flush=True)


if __name__ == "__main__":
    main()
