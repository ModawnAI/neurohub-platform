#!/usr/bin/env python3
"""End-to-End test with sub-001 real data (T1 + DTI).

Runs the full NeuroHub pipeline on the server:
1. Extract sub-001_raw.zip → BIDS conversion
2. Pre-QC validation
3. Execute technique containers (Cortical_Thickness, Diffusion_Properties, Tractography)
4. Fusion engine
5. Print final results

Usage:
    python scripts/test_e2e_sub001.py [--skip-containers] [--input-dir /path/to/sub-001]

Requires:
    - Docker images built: neurohub/cortical-thickness:1.0.0, neurohub/diffusion-properties:1.0.0, neurohub/tractography:1.0.0
    - FreeSurfer, FSL, MRtrix3 installed at standard paths
    - Pre-computed FreeSurfer data at /projects4/NEUROHUB/TEST/INPUT/freesurfer/ (optional, saves hours)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.bids_converter import (
    convert_dicom_to_nifti,
    classify_modality,
    filter_by_slice_count,
    select_best_per_modality,
    organize_bids,
    decompress_upload,
)
from app.services.pre_qc import (
    check_minimum_requirements,
)
from app.services.technique_output import validate_technique_output
from app.services.fusion_engine import FusionConfig, run_fusion


# Default paths on the server
DEFAULT_INPUT = "/projects4/NEUROHUB/TEST/INPUT/sub-001_raw.zip"
DEFAULT_FREESURFER = "/projects4/NEUROHUB/TEST/INPUT/freesurfer"
DEFAULT_OUTPUT = "/projects4/NEUROHUB/TEST/OUTPUT/e2e_test"

# Technique weights matching Parkinson Dx service
TECHNIQUE_WEIGHTS = {
    "Cortical_Thickness": 0.15,
    "Diffusion_Properties": 0.20,
    # Tractography doesn't have a weight in Parkinson Dx but we test it anyway
}

# Docker images
CONTAINER_IMAGES = {
    "Cortical_Thickness": "neurohub/cortical-thickness:1.0.0",
    "Diffusion_Properties": "neurohub/diffusion-properties:1.0.0",
    "Tractography": "neurohub/tractography:1.0.0",
}

# Host mount paths
HOST_MOUNTS = {
    "/usr/local/freesurfer/8.0.0": "/opt/freesurfer",
    "/usr/local/fsl": "/opt/fsl",
    "/usr/local/mrtrix3": "/opt/mrtrix3",
}


def banner(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


async def run_container(
    technique_key: str,
    docker_image: str,
    input_dir: str,
    output_dir: str,
    extra_env: dict[str, str] | None = None,
    extra_mounts: dict[str, str] | None = None,
) -> dict | None:
    """Run a technique container and return parsed NEUROHUB_OUTPUT."""
    os.makedirs(output_dir, exist_ok=True)

    cmd = ["docker", "run", "--rm"]

    # Mounts
    cmd.extend(["-v", f"{input_dir}:/input:ro"])
    cmd.extend(["-v", f"{output_dir}:/output"])

    all_mounts = {**HOST_MOUNTS}
    if extra_mounts:
        all_mounts.update(extra_mounts)

    for host, container in all_mounts.items():
        if Path(host).exists():
            cmd.extend(["-v", f"{host}:{container}:ro"])

    # Env
    if extra_env:
        for k, v in extra_env.items():
            cmd.extend(["-e", f"{k}={v}"])

    cmd.extend(["--memory", "16g"])
    cmd.append(docker_image)

    print(f"[e2e] Running container: {technique_key}")
    print(f"[e2e] Image: {docker_image}")
    print(f"[e2e] Input: {input_dir}")
    print(f"[e2e] Output: {output_dir}")

    start = time.monotonic()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    elapsed = time.monotonic() - start

    stdout_str = stdout.decode("utf-8", errors="replace")
    stderr_str = stderr.decode("utf-8", errors="replace")

    print(f"[e2e] {technique_key} completed in {elapsed:.1f}s (exit={proc.returncode})")

    if stdout_str:
        # Show last 20 lines
        lines = stdout_str.strip().splitlines()
        for line in lines[-20:]:
            print(f"  | {line}")

    if proc.returncode != 0:
        print(f"[e2e] STDERR: {stderr_str[-500:]}")
        return None

    # Parse NEUROHUB_OUTPUT
    for line in stdout_str.splitlines():
        if line.startswith("NEUROHUB_OUTPUT:"):
            json_str = line[len("NEUROHUB_OUTPUT:"):].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                print(f"[e2e] Failed to parse output JSON")
                return None

    print(f"[e2e] WARNING: No NEUROHUB_OUTPUT found in container logs")
    return None


async def main():
    parser = argparse.ArgumentParser(description="E2E test with sub-001")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT, help="Path to sub-001_raw.zip or extracted dir")
    parser.add_argument("--freesurfer-dir", default=DEFAULT_FREESURFER, help="Pre-computed FreeSurfer output")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT, help="Output directory")
    parser.add_argument("--skip-containers", action="store_true", help="Skip container execution, use mock data")
    parser.add_argument("--skip-bids", action="store_true", help="Skip BIDS conversion (use existing)")
    parser.add_argument("--streamlines", type=int, default=10000, help="Number of streamlines for tractography")
    args = parser.parse_args()

    output_base = Path(args.output_dir)
    output_base.mkdir(parents=True, exist_ok=True)

    # ========================================
    # Stage 1: BIDS Conversion
    # ========================================
    banner("Stage 1: BIDS Conversion")

    bids_dir = output_base / "bids"

    if args.skip_bids and bids_dir.exists():
        print("[e2e] Skipping BIDS conversion (using existing)")
    else:
        input_path = args.input_dir

        # Extract if zip
        if input_path.endswith(".zip"):
            print(f"[e2e] Extracting {input_path}...")
            extract_dir = str(output_base / "extracted")
            await decompress_upload(input_path, extract_dir)
            input_path = extract_dir

        print(f"[e2e] Converting DICOM → NIfTI...")
        nifti_dir = str(output_base / "nifti")
        volumes = await convert_dicom_to_nifti(input_path, nifti_dir)
        print(f"[e2e] Found {len(volumes)} NIfTI volumes")

        for vol in volumes:
            modality = await classify_modality(vol.get("json_sidecar", {}))
            vol["modality"] = modality
            print(f"  - {vol.get('nifti_path', '?')}: {modality}")

        # Filter by slice count
        valid, skipped = filter_by_slice_count(volumes)
        print(f"[e2e] Valid volumes: {len(valid)}, Skipped: {len(skipped)}")

        # Select best per modality
        selected = select_best_per_modality(valid)
        print(f"[e2e] Selected modalities: {list(selected.keys())}")

        # Organize BIDS
        bids_path = await organize_bids(selected, "sub-001", "ses-01")
        bids_dir = Path(bids_path)
        print(f"[e2e] BIDS directory: {bids_dir}")

    # ========================================
    # Stage 2: Pre-QC
    # ========================================
    banner("Stage 2: Pre-QC Validation")

    anat_dir = bids_dir / "sub-001" / "ses-01" / "anat" if (bids_dir / "sub-001").exists() else bids_dir / "anat"
    dwi_dir = bids_dir / "sub-001" / "ses-01" / "dwi" if (bids_dir / "sub-001").exists() else bids_dir / "dwi"

    # Check T1
    t1_files = list(anat_dir.glob("*T1*")) if anat_dir.exists() else []
    dwi_files = list(dwi_dir.glob("*.nii*")) if dwi_dir.exists() else []
    print(f"[e2e] T1 files: {len(t1_files)}")
    print(f"[e2e] DWI files: {len(dwi_files)}")

    for f in t1_files:
        json_sidecar = f.with_suffix("").with_suffix(".json") if f.name.endswith(".gz") else f.with_suffix(".json")
        if json_sidecar.exists():
            sidecar = json.loads(json_sidecar.read_text())
            checks = check_minimum_requirements(sidecar, str(f), "T1")
            for chk in checks:
                status_icon = "✓" if chk.status == "PASS" else ("⚠" if chk.status == "WARN" else "✗")
                print(f"  {status_icon} [{chk.check_type}] {chk.message_ko}")

    # ========================================
    # Stage 3: Technique Execution
    # ========================================
    banner("Stage 3: Technique Container Execution")

    technique_outputs: list[dict] = []

    if args.skip_containers:
        print("[e2e] Skipping containers — using mock outputs")
        technique_outputs = [
            {
                "module": "Cortical_Thickness",
                "module_version": "1.0.0",
                "qc_score": 88.0,
                "qc_flags": [],
                "features": {"global_mean_thickness": 2.65, "mean_thickness_lh": 2.63, "mean_thickness_rh": 2.67},
                "maps": {},
                "confidence": 79.2,
            },
            {
                "module": "Diffusion_Properties",
                "module_version": "1.0.0",
                "qc_score": 85.0,
                "qc_flags": [],
                "features": {"mean_fa": 0.42, "mean_md": 0.00078, "mean_rd": 0.00055, "mean_ad": 0.00125},
                "maps": {},
                "confidence": 72.3,
            },
        ]
    else:
        # Determine input for containers
        container_input = str(bids_dir)

        # Copy FreeSurfer data into BIDS structure if available
        fs_src = Path(args.freesurfer_dir)
        if fs_src.exists():
            fs_dst = bids_dir / "freesurfer"
            if not fs_dst.exists():
                print(f"[e2e] Copying pre-computed FreeSurfer to {fs_dst}")
                shutil.copytree(fs_src, fs_dst)

        # Container 1: Cortical Thickness
        ct_output_dir = str(output_base / "technique_outputs" / "cortical_thickness")
        ct_result = await run_container(
            "Cortical_Thickness",
            CONTAINER_IMAGES["Cortical_Thickness"],
            container_input,
            ct_output_dir,
            extra_env={"NEUROHUB_SKIP_RECON": "1", "NTHREADS": "4"},
        )
        if ct_result:
            technique_outputs.append(ct_result)

        # Container 2: Diffusion Properties
        dp_output_dir = str(output_base / "technique_outputs" / "diffusion_properties")
        dp_result = await run_container(
            "Diffusion_Properties",
            CONTAINER_IMAGES["Diffusion_Properties"],
            container_input,
            dp_output_dir,
        )
        if dp_result:
            technique_outputs.append(dp_result)

        # Container 3: Tractography (needs FreeSurfer for ACT)
        tck_output_dir = str(output_base / "technique_outputs" / "tractography")
        tck_result = await run_container(
            "Tractography",
            CONTAINER_IMAGES["Tractography"],
            container_input,
            tck_output_dir,
            extra_env={"STREAMLINE_COUNT": str(args.streamlines)},
        )
        if tck_result:
            technique_outputs.append(tck_result)

    print(f"\n[e2e] Completed {len(technique_outputs)} techniques")
    for out in technique_outputs:
        print(f"  - {out['module']}: QC={out['qc_score']}, features={len(out.get('features', {}))}")

    # ========================================
    # Stage 4: Fusion Engine
    # ========================================
    banner("Stage 4: Fusion Engine")

    if len(technique_outputs) < 1:
        print("[e2e] ERROR: No technique outputs to fuse")
        sys.exit(1)

    # Validate outputs
    validated = []
    for raw in technique_outputs:
        try:
            out = validate_technique_output(raw, raw["module"])
            validated.append(out)
        except ValueError as e:
            print(f"[e2e] WARNING: Invalid output for {raw.get('module')}: {e}")

    # Run fusion
    config = FusionConfig(
        service_id="e2e-test",
        technique_weights=TECHNIQUE_WEIGHTS,
    )

    try:
        fusion = run_fusion(validated, config)
        print(f"[e2e] Fusion result:")
        print(f"  Engine: {fusion.fusion_engine} v{fusion.fusion_version}")
        print(f"  Included: {fusion.included_modules}")
        print(f"  Excluded: {fusion.excluded_modules}")
        print(f"  Confidence: {fusion.confidence_score:.1f}")
        print(f"  Concordance: {fusion.concordance_score:.3f}")
        print(f"  QC Summary: mean={fusion.qc_summary['mean_qc']:.1f}, min={fusion.qc_summary['min_qc']:.1f}")
        print(f"  Results: {json.dumps(fusion.results, indent=2)}")

        # Save fusion result
        fusion_path = output_base / "fusion_result.json"
        fusion_dict = {
            "service_id": fusion.service_id,
            "fusion_engine": fusion.fusion_engine,
            "fusion_version": fusion.fusion_version,
            "included_modules": fusion.included_modules,
            "excluded_modules": fusion.excluded_modules,
            "qc_summary": fusion.qc_summary,
            "results": fusion.results,
            "probability_maps": fusion.probability_maps,
            "confidence_score": fusion.confidence_score,
            "concordance_score": fusion.concordance_score,
        }
        fusion_path.write_text(json.dumps(fusion_dict, indent=2, ensure_ascii=False))
        print(f"\n[e2e] Fusion result saved: {fusion_path}")

    except ValueError as e:
        print(f"[e2e] Fusion failed: {e}")
        sys.exit(1)

    # ========================================
    # Summary
    # ========================================
    banner("E2E Test Complete")
    print(f"Input: {args.input_dir}")
    print(f"Output: {output_base}")
    print(f"Techniques: {len(technique_outputs)}")
    print(f"Fusion confidence: {fusion.confidence_score:.1f}")
    print(f"Fusion concordance: {fusion.concordance_score:.3f}")
    print(f"\nAll outputs in: {output_base}")


if __name__ == "__main__":
    asyncio.run(main())
