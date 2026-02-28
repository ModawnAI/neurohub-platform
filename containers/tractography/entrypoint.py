#!/usr/bin/env python3
"""NeuroHub Tractography technique container entrypoint.

Wraps MRtrix3 CSD + tckgen for whole-brain tractography.
Outputs NEUROHUB_OUTPUT JSON to stdout.

Mounts:
  /input  — BIDS input (expects dwi/*.nii.gz + .bvec + .bval, freesurfer/ for ACT)
  /output — output directory
  /opt/mrtrix3 — host-mounted MRtrix3 (read-only)
  /opt/fsl — host-mounted FSL (read-only)
  /opt/freesurfer — host-mounted FreeSurfer (read-only)

Environment:
  STREAMLINE_COUNT — number of streamlines (default: 10000 for quick test)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

MODULE_KEY = "Tractography"
MODULE_VERSION = "1.0.0"


def setup_env() -> dict[str, str]:
    """Set up PATH with host-mounted tools."""
    env = os.environ.copy()
    fsl_dir = os.environ.get("FSLDIR", "/opt/fsl")
    mrtrix_dir = os.environ.get("MRTRIX_DIR", "/opt/mrtrix3")
    fs_home = os.environ.get("FREESURFER_HOME", "/opt/freesurfer")

    env["FSLDIR"] = fsl_dir
    env["FSLOUTPUTTYPE"] = "NIFTI_GZ"
    env["FREESURFER_HOME"] = fs_home
    env["PATH"] = f"{mrtrix_dir}/bin:{fsl_dir}/bin:{fsl_dir}/share/fsl/bin:{fs_home}/bin:{env.get('PATH', '')}"

    return env


def run_cmd(cmd: list[str], env: dict, desc: str, timeout: int = 7200) -> subprocess.CompletedProcess:
    """Run command with logging."""
    print(f"[tractography] {desc}...", flush=True)
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        print(f"[tractography] STDERR: {result.stderr[-1000:]}", file=sys.stderr, flush=True)
        raise RuntimeError(f"{desc} failed (exit {result.returncode})")
    return result


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
    return None


def find_preprocessed_dwi(input_dir: Path) -> Path | None:
    """Find preprocessed DWI from diffusion-properties output."""
    candidates = [
        input_dir / "dwi" / "reproc" / "post_preproc.nii.gz",
        input_dir / "dwi" / "reproc" / "post_preproc.mif",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def main():
    input_dir = Path("/input")
    output_dir = Path("/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    env = setup_env()
    work_dir = output_dir / "work"
    work_dir.mkdir(exist_ok=True)

    streamline_count = int(os.environ.get("STREAMLINE_COUNT", "10000"))

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
    print(f"[tractography] DWI: {dwi_nii.name}", flush=True)
    print(f"[tractography] Streamlines: {streamline_count}", flush=True)

    # Step 1: Convert DWI
    dwi_mif = work_dir / "dwi.mif"
    run_cmd(
        ["mrconvert", str(dwi_nii), str(dwi_mif),
         "-fslgrad", str(bvec), str(bval), "-force"],
        env, "Converting DWI to MIF"
    )

    # Step 2: Brain mask
    mask = work_dir / "mask.mif"
    run_cmd(
        ["dwi2mask", str(dwi_mif), str(mask), "-force"],
        env, "Creating brain mask"
    )

    # Step 3: Response function estimation (single-shell CSD)
    wm_response = work_dir / "wm_response.txt"
    gm_response = work_dir / "gm_response.txt"
    csf_response = work_dir / "csf_response.txt"

    # Try dhollander (multi-tissue), fallback to tournier (single-shell)
    try:
        run_cmd(
            ["dwi2response", "dhollander", str(dwi_mif),
             str(wm_response), str(gm_response), str(csf_response),
             "-mask", str(mask), "-force"],
            env, "Estimating response functions (dhollander)"
        )
        multi_tissue = True
    except RuntimeError:
        run_cmd(
            ["dwi2response", "tournier", str(dwi_mif), str(wm_response),
             "-mask", str(mask), "-force"],
            env, "Estimating response function (tournier)"
        )
        multi_tissue = False

    # Step 4: FOD estimation
    wm_fod = work_dir / "wm_fod.mif"
    if multi_tissue:
        gm_fod = work_dir / "gm_fod.mif"
        csf_fod = work_dir / "csf_fod.mif"
        run_cmd(
            ["dwi2fod", "msmt_csd", str(dwi_mif),
             str(wm_response), str(wm_fod),
             str(gm_response), str(gm_fod),
             str(csf_response), str(csf_fod),
             "-mask", str(mask), "-force"],
            env, "Computing FODs (multi-tissue CSD)"
        )
    else:
        run_cmd(
            ["dwi2fod", "csd", str(dwi_mif), str(wm_response), str(wm_fod),
             "-mask", str(mask), "-force"],
            env, "Computing FODs (single-shell CSD)"
        )

    # Step 5: Try ACT (Anatomically-Constrained Tractography) with FreeSurfer
    use_act = False
    ftt_image = work_dir / "5tt.mif"
    fs_dir = input_dir / "freesurfer"

    if fs_dir.exists() and (fs_dir / "mri" / "aparc+aseg.mgz").exists():
        try:
            # Fix FreeSurfer 8.0 LUT inconsistency: sclimbic entries have 7 columns
            # instead of 6, which breaks MRtrix3's labelconvert.
            # Create a patched FREESURFER_HOME with sanitized LUT.
            patched_fs = work_dir / "freesurfer_patched"
            patched_fs.mkdir(exist_ok=True)

            orig_lut = Path(env.get("FREESURFER_HOME", "/opt/freesurfer")) / "FreeSurferColorLUT.txt"
            if orig_lut.exists():
                sanitized_lines = []
                for line in orig_lut.read_text().splitlines():
                    stripped = line.strip()
                    # Skip comments and blank lines
                    if not stripped or stripped.startswith("#"):
                        sanitized_lines.append(line)
                        continue
                    parts = stripped.split()
                    if len(parts) >= 6:
                        # Keep only first 6 columns: index name R G B A
                        sanitized_lines.append(f"{parts[0]:>4s} {parts[1]:<50s} {parts[2]:>3s} {parts[3]:>3s} {parts[4]:>3s} {parts[5]:>3s}")
                    else:
                        sanitized_lines.append(line)
                (patched_fs / "FreeSurferColorLUT.txt").write_text("\n".join(sanitized_lines) + "\n")
                print("[tractography] Patched FreeSurferColorLUT.txt (fixed 7-column sclimbic entries)", flush=True)

                # Symlink everything else from the real FREESURFER_HOME
                real_fs = Path(env.get("FREESURFER_HOME", "/opt/freesurfer"))
                for item in real_fs.iterdir():
                    if item.name != "FreeSurferColorLUT.txt":
                        target = patched_fs / item.name
                        if not target.exists():
                            target.symlink_to(item)

                # Use patched FREESURFER_HOME for 5ttgen
                act_env = {**env, "FREESURFER_HOME": str(patched_fs)}
            else:
                act_env = env

            # Generate 5TT image from FreeSurfer
            run_cmd(
                ["5ttgen", "freesurfer", str(fs_dir / "mri" / "aparc+aseg.mgz"),
                 str(ftt_image), "-force"],
                act_env, "Generating 5TT from FreeSurfer"
            )
            use_act = True
        except RuntimeError:
            print("[tractography] 5TT generation failed, running without ACT", flush=True)

    # Step 6: Generate tractogram
    tck_file = output_dir / f"WBT_{streamline_count}.tck"
    tckgen_cmd = [
        "tckgen", str(wm_fod), str(tck_file),
        "-select", str(streamline_count),
        "-seed_dynamic", str(wm_fod),
        "-maxlength", "250",
        "-minlength", "10",
        "-cutoff", "0.06",
        "-force",
    ]

    if use_act:
        tckgen_cmd.extend(["-act", str(ftt_image), "-backtrack"])

    run_cmd(tckgen_cmd, env, f"Generating {streamline_count} streamlines")

    # Step 7: Get tractogram statistics
    features: dict[str, float] = {}
    try:
        result = run_cmd(
            ["tckstats", str(tck_file), "-dump", str(work_dir / "lengths.txt")],
            env, "Computing tractogram statistics"
        )
        # Parse tckstats output
        for line in result.stdout.splitlines():
            if "mean" in line.lower():
                parts = line.split()
                for p in parts:
                    try:
                        features["mean_length"] = float(p)
                        break
                    except ValueError:
                        continue

        # Read lengths file for more stats
        lengths_file = work_dir / "lengths.txt"
        if lengths_file.exists():
            lengths = [float(l) for l in lengths_file.read_text().splitlines() if l.strip()]
            if lengths:
                features["streamline_count"] = float(len(lengths))
                features["mean_length"] = round(sum(lengths) / len(lengths), 2)
                features["min_length"] = round(min(lengths), 2)
                features["max_length"] = round(max(lengths), 2)
                features["median_length"] = round(sorted(lengths)[len(lengths) // 2], 2)
    except RuntimeError:
        features["streamline_count"] = float(streamline_count)

    # Step 8: Generate connectivity matrix if atlas available
    connectome_file = output_dir / "connectome.csv"
    atlas_file = None

    # Check for DK atlas from FreeSurfer
    if fs_dir.exists():
        for candidate in [fs_dir / "mri" / "dk84.nii", fs_dir / "mri" / "aparc+aseg.nii"]:
            if candidate.exists():
                atlas_file = candidate
                break

    if atlas_file and tck_file.exists():
        try:
            run_cmd(
                ["tck2connectome", str(tck_file), str(atlas_file), str(connectome_file),
                 "-symmetric", "-zero_diagonal", "-force"],
                env, "Computing connectivity matrix"
            )
            # Count non-zero connections
            if connectome_file.exists():
                import csv
                with open(connectome_file) as f:
                    reader = csv.reader(f)
                    matrix = [list(map(float, row)) for row in reader if row]
                    n_regions = len(matrix)
                    n_connections = sum(1 for row in matrix for val in row if val > 0)
                    features["n_atlas_regions"] = float(n_regions)
                    features["n_connections"] = float(n_connections)
                    features["connectivity_density"] = round(
                        n_connections / (n_regions * (n_regions - 1)) if n_regions > 1 else 0, 4
                    )
        except (RuntimeError, Exception) as e:
            print(f"[tractography] Connectome generation failed: {e}", flush=True)

    # QC score
    qc_flags: list[str] = []
    qc_score = 85.0
    actual_count = features.get("streamline_count", float(streamline_count))

    if actual_count >= streamline_count * 0.9:
        qc_score = 90.0
    elif actual_count >= streamline_count * 0.5:
        qc_score = 70.0
        qc_flags.append("LOW_STREAMLINE_YIELD")
    else:
        qc_score = 40.0
        qc_flags.append("VERY_LOW_STREAMLINE_YIELD")

    if use_act:
        qc_score = min(qc_score + 5, 100.0)  # Bonus for ACT
    else:
        qc_flags.append("NO_ACT_CONSTRAINT")

    maps: dict[str, str] = {"tractogram": str(tck_file)}
    if connectome_file.exists():
        maps["connectome"] = str(connectome_file)

    output = {
        "module": MODULE_KEY,
        "module_version": MODULE_VERSION,
        "qc_score": round(qc_score, 1),
        "qc_flags": qc_flags,
        "features": features,
        "maps": maps,
        "confidence": round(qc_score * 0.85, 1),
    }

    print(f"[tractography] Generated {int(actual_count)} streamlines, QC={qc_score:.1f}", flush=True)
    print(f"NEUROHUB_OUTPUT: {json.dumps(output)}", flush=True)


if __name__ == "__main__":
    main()
