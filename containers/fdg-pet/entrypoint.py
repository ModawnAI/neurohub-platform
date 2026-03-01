#!/usr/bin/env python3
"""NeuroHub FDG-PET technique container entrypoint.

Wraps the neuroan_pet MATLAB/SPM25 pipeline for FDG-PET analysis.
Outputs NEUROHUB_OUTPUT JSON to stdout.

neuroan_pet_run(inputDir, ID, envFile) expects:
  inputDir/PET_tr/   — PET DICOM series
  inputDir/preT1/    — T1 MRI DICOM series

Pipeline stages:
  0. DICOM→NIfTI (spm_dicom_convert)
  1. Preprocess (coregistration + normalization + 6mm smoothing)
  2. Statistics (ROI z-score + SPM two-sample t-test vs normal controls)
  3. Report generation (HTML with MIP + Colin27 3D render)

Mounts:
  /input           — subject data (PET_tr/ + preT1/ DICOMs, or BIDS NIfTI)
  /output          — output directory
  /opt/matlab      — host-mounted MATLAB R2025b (read-only)
  /opt/spm25       — host-mounted SPM25 (read-only)
  /opt/neuroan_pet — host-mounted neuroan_pet code (read-only)
  /opt/neuroan_db  — host-mounted normal control database (read-only)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MODULE_KEY = "FDG_PET"
MODULE_VERSION = "1.0.0"


def setup_env() -> dict[str, str]:
    """Set up environment for MATLAB execution."""
    env = os.environ.copy()
    matlab_home = os.environ.get("MATLAB_HOME", "/opt/matlab")

    env["MATLAB_HOME"] = matlab_home
    env["MLM_LICENSE_FILE"] = os.environ.get(
        "MLM_LICENSE_FILE", f"{matlab_home}/licenses"
    )

    # MATLAB needs a writable home with .matlab preferences directory
    # Must exist BEFORE matlab binary starts (it checks during JVM init)
    matlab_user_home = Path("/tmp/matlab_user")
    matlab_user_home.mkdir(parents=True, exist_ok=True)
    prefs_dir = matlab_user_home / ".matlab" / "R2025b"
    prefs_dir.mkdir(parents=True, exist_ok=True)

    # Also create MATLAB log/temp directories it may need
    (matlab_user_home / ".MathWorks").mkdir(parents=True, exist_ok=True)
    (Path("/tmp") / "mathworks_tmp").mkdir(parents=True, exist_ok=True)

    env["HOME"] = str(matlab_user_home)
    env["TMPDIR"] = "/tmp"
    env["MATLAB_PREFDIR"] = str(prefs_dir)
    env["MATLAB_LOG_DIR"] = "/tmp"
    env["MATLAB_USE_USERWORK"] = "0"
    env["MW_SERVICEHOST_DISABLE"] = "1"
    env["MATLABPATH"] = ""

    # Start Xvfb for headless rendering (report generation needs display)
    _start_xvfb(env)
    env["PATH"] = f"{matlab_home}/bin:{env.get('PATH', '')}"
    env["LD_LIBRARY_PATH"] = (
        f"{matlab_home}/bin/glnxa64:{matlab_home}/sys/os/glnxa64:"
        + env.get("LD_LIBRARY_PATH", "")
    )
    return env


def _start_xvfb(env: dict[str, str]) -> None:
    """Start Xvfb virtual framebuffer for headless rendering."""
    try:
        xvfb = subprocess.Popen(
            ["Xvfb", ":99", "-screen", "0", "1024x768x24", "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        env["DISPLAY"] = ":99"
        import time
        time.sleep(1)  # Wait for Xvfb to start
        print("[fdg-pet] Xvfb started on :99", flush=True)
    except FileNotFoundError:
        print("[fdg-pet] Xvfb not available, skipping display setup", flush=True)
        env.pop("DISPLAY", None)


def get_matlab_prefdir() -> str:
    """Return the prefdir path for MATLAB command-line arg."""
    return "/tmp/matlab_user/.matlab/R2025b"


def run_matlab(
    cmd: list[str], env: dict, desc: str, timeout: int = 3600,
    log_dir: Path | None = None,
) -> tuple[int, str, str]:
    """Run MATLAB with proper handling of MathWorksServiceHost daemon.

    MATLAB R2025b spawns a ServiceHost background process that inherits
    stdout/stderr pipes, preventing subprocess.run(capture_output=True) from
    returning even after MATLAB exits. We use Popen with a polling loop
    to detect MATLAB exit and then kill remaining child processes.
    """
    import signal
    import time as _time

    print(f"[fdg-pet] {desc}...", flush=True)

    stdout_file = (log_dir / "matlab_stdout.log") if log_dir else Path("/tmp/matlab_stdout.log")
    stderr_file = (log_dir / "matlab_stderr.log") if log_dir else Path("/tmp/matlab_stderr.log")
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

    with open(stdout_file, "w") as fout, open(stderr_file, "w") as ferr:
        proc = subprocess.Popen(
            cmd, env=env, stdout=fout, stderr=ferr,
        )

        start = _time.monotonic()
        while True:
            ret = proc.poll()
            if ret is not None:
                break
            if _time.monotonic() - start > timeout:
                proc.kill()
                proc.wait()
                print(f"[fdg-pet] {desc} timed out after {timeout}s", flush=True)
                return 124, "", f"Timed out after {timeout}s"
            _time.sleep(2)

    # Kill any remaining child processes (MathWorksServiceHost)
    _kill_children()

    stdout = stdout_file.read_text() if stdout_file.exists() else ""
    stderr = stderr_file.read_text() if stderr_file.exists() else ""

    # Print MATLAB output
    if stdout:
        for line in stdout.splitlines()[-50:]:
            print(f"[fdg-pet] MATLAB> {line}", flush=True)

    if ret != 0:
        print(f"[fdg-pet] STDOUT tail: {stdout[-2000:] or '(empty)'}", flush=True)
        print(f"[fdg-pet] STDERR tail: {stderr[-2000:] or '(empty)'}", file=sys.stderr, flush=True)

    return ret, stdout, stderr


def _kill_children():
    """Kill remaining child processes (e.g. MathWorksServiceHost)."""
    import signal

    my_pid = os.getpid()
    try:
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            if pid == my_pid:
                continue
            try:
                stat = (entry / "stat").read_text()
                ppid = int(stat.split(")")[1].split()[1])
                if ppid == my_pid:
                    cmdline = (entry / "cmdline").read_text()
                    print(f"[fdg-pet] Killing child process {pid}: {cmdline[:80]}", flush=True)
                    os.kill(pid, signal.SIGKILL)
            except (FileNotFoundError, ProcessLookupError, ValueError, IndexError):
                pass
    except Exception as e:
        print(f"[fdg-pet] Child cleanup: {e}", flush=True)


def detect_input_format(input_dir: Path) -> str:
    """Detect whether input is raw DICOM (PET_tr/preT1) or BIDS NIfTI.

    Returns: 'dicom_raw' | 'bids' | 'nifti_flat'
    """
    if (input_dir / "PET_tr").exists():
        return "dicom_raw"
    if (input_dir / "pet").exists() or (input_dir / "anat").exists():
        return "bids"
    for nii in input_dir.glob("*.nii*"):
        return "nifti_flat"
    return "unknown"


def prepare_dicom_input(input_dir: Path, work_dir: Path) -> Path:
    """Prepare input directory in the format neuroan_pet expects.

    neuroan_pet_run expects inputDir/PET_tr/ and inputDir/preT1/.
    If input is already in that format (read-only mount), copy to writable work_dir.
    """
    subject_dir = work_dir / "subject"
    subject_dir.mkdir(exist_ok=True)

    # Input is read-only, so we need a writable copy for neuroan_pet
    # (it writes nii/ and intermediate files into the input directory)
    pet_tr = input_dir / "PET_tr"
    pre_t1 = input_dir / "preT1"

    if pet_tr.exists():
        dst = subject_dir / "PET_tr"
        if not dst.exists():
            shutil.copytree(str(pet_tr), str(dst))
        print(f"[fdg-pet] PET_tr: {len(list(dst.iterdir()))} files", flush=True)

    if pre_t1.exists():
        dst = subject_dir / "preT1"
        if not dst.exists():
            shutil.copytree(str(pre_t1), str(dst))
        print(f"[fdg-pet] preT1: {len(list(dst.iterdir()))} files", flush=True)

    return subject_dir


def prepare_bids_input(input_dir: Path, work_dir: Path) -> tuple[Path | None, Path | None]:
    """Extract NIfTI paths from BIDS input structure."""
    pet_nii = None
    t1_nii = None

    pet_dir = input_dir / "pet"
    if pet_dir.exists():
        for nii in sorted(pet_dir.glob("*.nii*")):
            pet_nii = nii
            break

    anat_dir = input_dir / "anat"
    if anat_dir.exists():
        for nii in sorted(anat_dir.glob("*T1*.nii*")):
            t1_nii = nii
            break
        if not t1_nii:
            for nii in sorted(anat_dir.glob("*.nii*")):
                t1_nii = nii
                break

    return pet_nii, t1_nii


def generate_env_file(work_dir: Path) -> Path:
    """Generate neuroan_mps.env pointing to mounted paths."""
    neuroan_pet_home = os.environ.get("NEUROAN_PET_HOME", "/opt/neuroan_pet")
    neuroan_db_home = os.environ.get("NEUROAN_DB_HOME", "/opt/neuroan_db")

    env_content = f"""PET_TPM_DIR={neuroan_pet_home}/template
PET_ATL_DIR={neuroan_pet_home}/template
PET_NCDB_DIR={neuroan_db_home}/FDG-NC
SERVER_PUBLIC_DIR=/output
STATIC_IMAGE_DIR={neuroan_pet_home}/static
RENDER_DIR={neuroan_pet_home}/atlas
"""
    env_path = work_dir / "neuroan_mps.env"
    env_path.write_text(env_content)

    # neuroan_pet_reportgenerator uses loadenv() which looks for the env file
    # at a hardcoded path relative to HOME/Downloads/pet/. Place copies at all
    # possible HOME locations so MATLAB's loadenv() can find it.
    for home_dir in ["/tmp/matlab_user", "/root", os.environ.get("HOME", "/root")]:
        fallback_dir = Path(home_dir) / "Downloads" / "pet"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        (fallback_dir / "neuroan_mps.env").write_text(env_content)

    return env_path


def build_matlab_script(
    input_format: str,
    subject_dir: Path | None,
    pet_nii: Path | None,
    t1_nii: Path | None,
    output_dir: Path,
    work_dir: Path,
    env_file: Path,
    subject_id: str,
) -> Path:
    """Generate MATLAB wrapper script."""
    spm_home = os.environ.get("SPM_HOME", "/opt/spm25")
    neuroan_pet_home = os.environ.get("NEUROAN_PET_HOME", "/opt/neuroan_pet")
    neuroan_db_home = os.environ.get("NEUROAN_DB_HOME", "/opt/neuroan_db")

    if input_format == "dicom_raw" and subject_dir:
        # Call neuroan_pet_run directly — it handles DICOM→NIfTI internally
        matlab_code = f"""\
try
    fprintf('[fdg-pet] MATLAB started\\n');
    fprintf('[fdg-pet] MATLAB version: %s\\n', version);

    % Add SPM and neuroan_pet to path
    addpath('{spm_home}');
    fprintf('[fdg-pet] SPM added to path\\n');
    spm('defaults', 'PET');
    fprintf('[fdg-pet] SPM defaults set\\n');
    spm_jobman('initcfg');
    fprintf('[fdg-pet] SPM jobman initialized\\n');
    addpath(genpath('{neuroan_pet_home}'));
    fprintf('[fdg-pet] neuroan_pet added to path\\n');

    fprintf('[fdg-pet] Calling neuroan_pet_run...\\n');
    fprintf('[fdg-pet] inputDir: {subject_dir}\\n');
    fprintf('[fdg-pet] ID: {subject_id}\\n');
    fprintf('[fdg-pet] envFile: {env_file}\\n');

    % Verify env file exists
    if ~exist('{env_file}', 'file')
        error('Env file not found: {env_file}');
    end
    fprintf('[fdg-pet] Env file verified\\n');

    % Verify input dirs exist
    pet_dir = fullfile('{subject_dir}', 'PET_tr');
    t1_dir = fullfile('{subject_dir}', 'preT1');
    fprintf('[fdg-pet] PET_tr exists: %d\\n', exist(pet_dir, 'dir'));
    fprintf('[fdg-pet] preT1 exists: %d\\n', exist(t1_dir, 'dir'));

    neuroan_pet_run('{subject_dir}', '{subject_id}', '{env_file}');

    fprintf('[fdg-pet] neuroan_pet_run completed successfully\\n');

catch ME
    fprintf('[fdg-pet] ERROR: %s\\n', ME.message);
    fprintf('[fdg-pet] ERROR ID: %s\\n', ME.identifier);
    for k = 1:numel(ME.stack)
        fprintf('[fdg-pet] STACK: %s (line %d)\\n', ME.stack(k).name, ME.stack(k).line);
    end
    % Also check for cause exceptions
    if ~isempty(ME.cause)
        for c = 1:numel(ME.cause)
            fprintf('[fdg-pet] CAUSE: %s\\n', ME.cause{{c}}.message);
        end
    end
end

% Copy key output files to /output regardless of error
fprintf('[fdg-pet] Copying output files...\\n');
nii_dir = fullfile('{subject_dir}', 'nii');
fprintf('[fdg-pet] nii_dir exists: %d\\n', exist(nii_dir, 'dir'));
if exist(nii_dir, 'dir')
    files = dir(fullfile(nii_dir, '**', '*.nii'));
    fprintf('[fdg-pet] Found %d NIfTI files in nii_dir\\n', numel(files));
    for i = 1:numel(files)
        src = fullfile(files(i).folder, files(i).name);
        dst = fullfile('{output_dir}', files(i).name);
        copyfile(src, dst);
        fprintf('[fdg-pet] Copied: %s\\n', files(i).name);
    end
    spm_files = dir(fullfile(nii_dir, '**', 'SPM.mat'));
    for i = 1:numel(spm_files)
        copyfile(fullfile(spm_files(i).folder, spm_files(i).name), ...
                 fullfile('{output_dir}', 'SPM.mat'));
    end
end

% Copy HTML report
html_files = dir(fullfile('{subject_dir}', '**', '*.html'));
fprintf('[fdg-pet] Found %d HTML files\\n', numel(html_files));
for i = 1:numel(html_files)
    copyfile(fullfile(html_files(i).folder, html_files(i).name), ...
             fullfile('{output_dir}', html_files(i).name));
end

fprintf('[fdg-pet] Pipeline finished\\n');
"""
    else:
        # BIDS/NIfTI input — run SPM preprocessing directly
        pet_path = str(pet_nii) if pet_nii else ""
        t1_path = str(t1_nii) if t1_nii else ""

        matlab_code = f"""\
addpath('{spm_home}');
spm('defaults', 'PET');
spm_jobman('initcfg');
addpath(genpath('{neuroan_pet_home}'));

fprintf('[fdg-pet] MATLAB started (BIDS/NIfTI mode)\\n');

pet_file = '{pet_path}';
t1_file = '{t1_path}';
env_file = '{env_file}';

% Load environment config
process = loadenv(env_file);

% Stage 1: Preprocess
fprintf('[fdg-pet] Stage 1: Preprocessing...\\n');
if ~isempty(t1_file)
    [state, swPETs, errLog] = neuroan_pet_preprocess(pet_file, t1_file, process);
else
    % Without T1, skip coregistration — just normalize + smooth
    fprintf('[fdg-pet] No T1, running normalization only\\n');
    matlabbatch = {{}};
    matlabbatch{{1}}.spm.spatial.normalise.estwrite.subj.vol = {{pet_file}};
    matlabbatch{{1}}.spm.spatial.normalise.estwrite.subj.resample = {{pet_file}};
    matlabbatch{{1}}.spm.spatial.normalise.estwrite.woptions.bb = [-78 -112 -70; 78 76 85];
    matlabbatch{{1}}.spm.spatial.normalise.estwrite.woptions.vox = [2 2 2];
    spm_jobman('run', matlabbatch);

    [pth, fn, ext] = fileparts(pet_file);
    w_file = fullfile(pth, ['w' fn ext]);
    matlabbatch = {{}};
    matlabbatch{{1}}.spm.spatial.smooth.data = {{w_file}};
    matlabbatch{{1}}.spm.spatial.smooth.fwhm = [6 6 6];
    spm_jobman('run', matlabbatch);
    swPETs = fullfile(pth, ['sw' fn ext]);
    state = 1;
end

if state == 1
    % Copy preprocessed files to output
    copyfile(swPETs, fullfile('{output_dir}', 'pet_smoothed.nii'));
    [pth, fn, ext] = fileparts(swPETs);
    w_file = strrep(swPETs, 'sw', 'w');
    if exist(w_file, 'file')
        copyfile(w_file, fullfile('{output_dir}', 'pet_normalized.nii'));
    end

    % Stage 2: Statistics
    fprintf('[fdg-pet] Stage 2: Statistics...\\n');
    try
        [state2, errLog2] = neuroan_pet_statistics(swPETs, process);
        fprintf('[fdg-pet] Statistics completed\\n');
        % Copy z-score map
        z_files = dir(fullfile(fileparts(swPETs), 'z_*.nii'));
        for i = 1:numel(z_files)
            copyfile(fullfile(z_files(i).folder, z_files(i).name), ...
                     fullfile('{output_dir}', z_files(i).name));
        end
        % Copy T-maps
        t_files = dir(fullfile(fileparts(swPETs), 'cond*.nii'));
        for i = 1:numel(t_files)
            copyfile(fullfile(t_files(i).folder, t_files(i).name), ...
                     fullfile('{output_dir}', t_files(i).name));
        end
        % Copy SPM.mat
        spm_mat = fullfile(fileparts(swPETs), 'SPM.mat');
        if exist(spm_mat, 'file')
            copyfile(spm_mat, fullfile('{output_dir}', 'SPM.mat'));
        end
    catch e
        fprintf('[fdg-pet] Statistics failed: %s\\n', e.message);
    end
end

fprintf('[fdg-pet] Pipeline finished\\n');
"""

    script_path = work_dir / "neurohub_fdg_pet.m"
    script_path.write_text(matlab_code)
    return script_path


def extract_features(output_dir: Path) -> dict[str, float]:
    """Extract quantitative features from neuroan_pet output files."""
    features: dict[str, float] = {}

    try:
        import nibabel as nib
        import numpy as np
    except ImportError:
        print("[fdg-pet] nibabel/numpy not available", flush=True)
        return features

    # Look for Z-score map (neuroan_pet outputs z_sw*.nii)
    z_candidates = sorted(output_dir.glob("z_*.nii*"))
    if not z_candidates:
        z_candidates = sorted(output_dir.glob("*zscore*.nii*"))
    if not z_candidates:
        z_candidates = sorted(output_dir.glob("*zmap*.nii*"))

    for zmap_path in z_candidates[:1]:
        try:
            img = nib.load(str(zmap_path))
            data = np.asarray(img.dataobj, dtype=np.float64)
            # Handle NaN values from mnet_zscore (std=0 voxels)
            valid_mask = np.isfinite(data) & (np.abs(data) > 0.01)
            if valid_mask.sum() > 100:
                brain_data = data[valid_mask]
                features["zscore_mean"] = round(float(np.nanmean(brain_data)), 4)
                features["zscore_std"] = round(float(np.nanstd(brain_data)), 4)
                features["zscore_min"] = round(float(np.nanmin(brain_data)), 4)
                features["zscore_max"] = round(float(np.nanmax(brain_data)), 4)
                hypo_count = int(np.sum(brain_data < -2))
                features["hypometabolic_voxels"] = float(hypo_count)
                features["hypometabolic_fraction"] = round(
                    hypo_count / valid_mask.sum(), 4
                )
                print(f"[fdg-pet] Z-score: mean={features['zscore_mean']}, "
                      f"hypo_frac={features['hypometabolic_fraction']}", flush=True)
        except Exception as e:
            print(f"[fdg-pet] Z-score extraction error: {e}", flush=True)

    # Look for T-maps (cond1 = NC>PT hypometabolism, cond2 = PT>NC hypermetabolism)
    for cond_name, label in [("cond1", "ncgt_pt"), ("cond2", "ptgt_nc")]:
        for tmap in sorted(output_dir.glob(f"{cond_name}*.nii*"))[:1]:
            try:
                img = nib.load(str(tmap))
                data = np.asarray(img.dataobj, dtype=np.float64)
                sig_voxels = np.sum(data > 0)
                if sig_voxels > 0:
                    features[f"tmap_{label}_voxels"] = float(sig_voxels)
                    features[f"tmap_{label}_max_t"] = round(float(np.max(data)), 4)
                    print(f"[fdg-pet] T-map {label}: {sig_voxels} voxels, "
                          f"max_t={features[f'tmap_{label}_max_t']}", flush=True)
            except Exception as e:
                print(f"[fdg-pet] T-map extraction error: {e}", flush=True)

    # Look for smoothed/warped PET
    for pattern in ["sw*.nii*", "pet_smoothed*.nii*"]:
        for norm_path in sorted(output_dir.glob(pattern))[:1]:
            try:
                img = nib.load(str(norm_path))
                data = np.asarray(img.dataobj, dtype=np.float64)
                positive = data[data > 0]
                if len(positive) > 100:
                    brain_mask = data > np.percentile(positive, 10)
                    brain_data = data[brain_mask]
                    features["mean_uptake"] = round(float(np.mean(brain_data)), 4)
                    features["std_uptake"] = round(float(np.std(brain_data)), 4)
                    features["global_metabolic_index"] = round(
                        float(np.mean(brain_data) / np.max(brain_data) * 100), 2
                    )
                    print(f"[fdg-pet] Uptake: mean={features['mean_uptake']}, "
                          f"GMI={features['global_metabolic_index']}", flush=True)
            except Exception as e:
                print(f"[fdg-pet] Uptake extraction error: {e}", flush=True)

    # Check for HTML report (neuroan_pet uses .htmx extension)
    for pattern in ["*.html", "*.htmx", "*.htm"]:
        for report in sorted(output_dir.glob(pattern)):
            features["report_generated"] = 1.0
            print(f"[fdg-pet] Report found: {report.name}", flush=True)
            break
        if "report_generated" in features:
            break

    return features


def collect_output_maps(output_dir: Path) -> dict[str, str]:
    """Collect output map file paths."""
    maps: dict[str, str] = {}

    # Z-score map
    for zmap in sorted(output_dir.glob("z_*.nii*")):
        maps["zscore_map"] = str(zmap)
        break

    # T-maps
    for tmap in sorted(output_dir.glob("cond1*.nii*")):
        maps["tmap_hypometabolic"] = str(tmap)
        break
    for tmap in sorted(output_dir.glob("cond2*.nii*")):
        maps["tmap_hypermetabolic"] = str(tmap)
        break

    # Smoothed warped PET
    for sw in sorted(output_dir.glob("sw*.nii*")) or sorted(output_dir.glob("pet_smoothed*.nii*")):
        maps["smoothed_pet"] = str(sw)
        break

    # Warped PET
    for w in sorted(output_dir.glob("w*.nii*")) or sorted(output_dir.glob("pet_normalized*.nii*")):
        if "sw" not in w.name:
            maps["normalized_pet"] = str(w)
            break

    # SPM.mat
    spm_mat = output_dir / "SPM.mat"
    if spm_mat.exists():
        maps["spm_design"] = str(spm_mat)

    # HTML report (neuroan_pet uses .htmx extension)
    for pattern in ["*.html", "*.htmx", "*.htm"]:
        for html in sorted(output_dir.glob(pattern)):
            maps["report_html"] = str(html)
            break
        if "report_html" in maps:
            break

    return maps


def compute_qc_score(features: dict[str, float], output_dir: Path) -> tuple[float, list[str]]:
    """Compute QC score based on output quality."""
    qc_score = 85.0
    qc_flags: list[str] = []

    # Check output maps exist
    nifti_count = len(list(output_dir.glob("*.nii*")))
    if nifti_count == 0:
        return 20.0, ["NO_OUTPUT_MAPS"]

    # Z-score quality
    if "zscore_mean" in features:
        if abs(features["zscore_mean"]) > 5:
            qc_score -= 15
            qc_flags.append("EXTREME_ZSCORE_MEAN")
    else:
        qc_score -= 10
        qc_flags.append("NO_ZSCORE_MAP")

    # Hypometabolic fraction sanity check
    hypo = features.get("hypometabolic_fraction", 0)
    if hypo > 0.5:
        qc_score -= 10
        qc_flags.append("HIGH_HYPOMETABOLIC_FRACTION")

    # T-map presence
    if "tmap_ncgt_pt_voxels" not in features and "tmap_ptgt_nc_voxels" not in features:
        qc_score -= 5
        qc_flags.append("NO_TMAP_RESULTS")

    # Report bonus
    if features.get("report_generated", 0) > 0:
        qc_score = min(qc_score + 5, 100)

    return round(max(0, min(100, qc_score)), 1), qc_flags


def main():
    input_dir = Path("/input")
    output_dir = Path("/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    env = setup_env()
    work_dir = output_dir / "work"
    work_dir.mkdir(exist_ok=True)

    # Validate MATLAB
    matlab_bin = Path(env.get("MATLAB_HOME", "/opt/matlab")) / "bin" / "matlab"
    if not matlab_bin.exists():
        print("[fdg-pet] ERROR: MATLAB not found", flush=True)
        output = {
            "module": MODULE_KEY, "module_version": MODULE_VERSION,
            "qc_score": 0.0, "qc_flags": ["MATLAB_NOT_FOUND"],
            "features": {}, "maps": {}, "confidence": 0.0,
        }
        print(f"NEUROHUB_OUTPUT: {json.dumps(output)}", flush=True)
        sys.exit(1)

    # Detect input format
    input_format = detect_input_format(input_dir)
    print(f"[fdg-pet] Input format: {input_format}", flush=True)

    subject_id = os.environ.get("SUBJECT_ID", "sub-001")
    subject_dir = None
    pet_nii = None
    t1_nii = None

    # Generate .env pointing to container mount paths
    env_file = generate_env_file(work_dir)

    if input_format == "dicom_raw":
        # neuroan_pet_run handles everything from DICOM
        subject_dir = prepare_dicom_input(input_dir, work_dir)
    elif input_format == "bids":
        pet_nii, t1_nii = prepare_bids_input(input_dir, work_dir)
        if not pet_nii:
            print("[fdg-pet] ERROR: No PET NIfTI in BIDS input", flush=True)
            output = {
                "module": MODULE_KEY, "module_version": MODULE_VERSION,
                "qc_score": 0.0, "qc_flags": ["NO_PET_INPUT"],
                "features": {}, "maps": {}, "confidence": 0.0,
            }
            print(f"NEUROHUB_OUTPUT: {json.dumps(output)}", flush=True)
            sys.exit(1)
    elif input_format == "nifti_flat":
        for nii in sorted(input_dir.glob("*.nii*")):
            pet_nii = nii
            break
        if not pet_nii:
            print("[fdg-pet] ERROR: No NIfTI files found", flush=True)
            output = {
                "module": MODULE_KEY, "module_version": MODULE_VERSION,
                "qc_score": 0.0, "qc_flags": ["NO_PET_INPUT"],
                "features": {}, "maps": {}, "confidence": 0.0,
            }
            print(f"NEUROHUB_OUTPUT: {json.dumps(output)}", flush=True)
            sys.exit(1)
    else:
        print("[fdg-pet] ERROR: Unknown input format", flush=True)
        output = {
            "module": MODULE_KEY, "module_version": MODULE_VERSION,
            "qc_score": 0.0, "qc_flags": ["UNKNOWN_INPUT_FORMAT"],
            "features": {}, "maps": {}, "confidence": 0.0,
        }
        print(f"NEUROHUB_OUTPUT: {json.dumps(output)}", flush=True)
        sys.exit(1)

    # Build and run MATLAB script
    matlab_script = build_matlab_script(
        input_format=input_format,
        subject_dir=subject_dir,
        pet_nii=pet_nii,
        t1_nii=t1_nii,
        output_dir=output_dir,
        work_dir=work_dir,
        env_file=env_file,
        subject_id=subject_id,
    )

    print(f"[fdg-pet] Running MATLAB pipeline...", flush=True)
    print(f"[fdg-pet] MATLAB script: {matlab_script}", flush=True)
    print(f"[fdg-pet] Script content:", flush=True)
    print(matlab_script.read_text()[:2000], flush=True)

    # Use -r instead of -batch for better compatibility in Docker containers.
    # -batch exits non-zero on any error; -r with explicit exit is more forgiving.
    exit_code, stdout, stderr = run_matlab(
        ["matlab", "-nodisplay", "-nosplash", "-r",
         f"try, run('{matlab_script}'), catch ME, "
         f"fprintf('[fdg-pet] MATLAB_ERROR: %s\\n', ME.message), "
         f"for k=1:numel(ME.stack), "
         f"fprintf('[fdg-pet] STACK: %s:%d\\n', ME.stack(k).name, ME.stack(k).line), "
         f"end, end, exit"],
        env, "Running neuroan_pet pipeline",
        timeout=3600,
        log_dir=work_dir,
    )
    if exit_code != 0:
        print(f"[fdg-pet] MATLAB exited with code {exit_code}", flush=True)
        if "license" in (stdout + stderr).lower():
            print("[fdg-pet] HINT: Possible MATLAB license issue", flush=True)

    # Also copy any outputs from subject_dir/nii/ to output_dir
    if subject_dir:
        nii_dir = subject_dir / "nii"
        if nii_dir.exists():
            for ext in ["*.nii", "*.html", "*.htmx", "*.htm", "*.png", "*.jpg"]:
                for f in nii_dir.rglob(ext):
                    dst = output_dir / f.name
                    if not dst.exists():
                        shutil.copy2(str(f), str(dst))
            for f in nii_dir.rglob("SPM.mat"):
                dst = output_dir / "SPM.mat"
                if not dst.exists():
                    shutil.copy2(str(f), str(dst))

    # Extract features and emit output
    features = extract_features(output_dir)
    maps = collect_output_maps(output_dir)
    qc_score, qc_flags = compute_qc_score(features, output_dir)

    output = {
        "module": MODULE_KEY,
        "module_version": MODULE_VERSION,
        "qc_score": qc_score,
        "qc_flags": qc_flags,
        "features": features,
        "maps": maps,
        "confidence": round(qc_score * 0.9, 1),
    }

    # Replace NaN/Inf with None for valid JSON
    import math
    clean_features = {}
    for k, v in features.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            clean_features[k] = 0.0
        else:
            clean_features[k] = v
    output["features"] = clean_features

    print(f"[fdg-pet] Extracted {len(features)} features, {len(maps)} maps, QC={qc_score}",
          flush=True)
    print(f"NEUROHUB_OUTPUT: {json.dumps(output)}", flush=True)


if __name__ == "__main__":
    main()
