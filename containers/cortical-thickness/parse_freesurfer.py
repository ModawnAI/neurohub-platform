"""Parse FreeSurfer stats files to extract cortical thickness and volumetric features."""

from __future__ import annotations

import re
from pathlib import Path


def parse_aparc_stats(stats_file: Path) -> dict[str, float]:
    """Parse ?h.aparc.stats to extract per-region cortical thickness and area."""
    features: dict[str, float] = {}
    if not stats_file.exists():
        return features

    hemi = "lh" if "lh." in stats_file.name else "rh"
    in_table = False

    for line in stats_file.read_text().splitlines():
        # Header: extract mean thickness
        if line.startswith("# MeanThickness"):
            parts = line.split(",")
            for part in parts:
                part = part.strip()
                if part.replace(".", "", 1).replace("-", "", 1).isdigit():
                    features[f"mean_thickness_{hemi}"] = float(part)

        # Table header marks start of data
        if line.startswith("# ColHeaders"):
            in_table = True
            continue

        if in_table and not line.startswith("#") and line.strip():
            cols = line.split()
            if len(cols) >= 5:
                region = cols[0]
                try:
                    surface_area = float(cols[2])
                    thickness = float(cols[4])
                    features[f"thickness_{hemi}_{region}"] = thickness
                    features[f"area_{hemi}_{region}"] = surface_area
                except (ValueError, IndexError):
                    pass

    return features


def parse_aseg_stats(stats_file: Path) -> dict[str, float]:
    """Parse aseg.stats to extract subcortical volumes."""
    features: dict[str, float] = {}
    if not stats_file.exists():
        return features

    for line in stats_file.read_text().splitlines():
        # Measure lines
        m = re.match(r"^# Measure (\S+),\s*\S+,\s*([\d.]+),\s*mm\^3", line)
        if m:
            name = m.group(1).lower()
            features[name] = float(m.group(2))
            continue

        # Table data
        if not line.startswith("#") and line.strip():
            cols = line.split()
            if len(cols) >= 5:
                region = cols[4] if len(cols) > 4 else cols[1]
                try:
                    volume = float(cols[3])
                    features[f"vol_{region}"] = volume
                except (ValueError, IndexError):
                    pass

    return features


def parse_euler_number(log_file: Path | None) -> float | None:
    """Extract Euler number from FreeSurfer log — lower absolute value = better quality."""
    if log_file is None or not log_file.exists():
        return None

    text = log_file.read_text()
    # Look for "euler number" in recon-all log
    matches = re.findall(r"euler\s+number\s*[=:]\s*(-?\d+)", text, re.IGNORECASE)
    if matches:
        return float(abs(int(matches[-1])))
    return None


def compute_qc_score(euler: float | None, features: dict[str, float]) -> float:
    """Compute QC score 0-100 based on Euler number and feature sanity."""
    score = 85.0  # default good

    if euler is not None:
        if euler < 50:
            score = 95.0
        elif euler < 100:
            score = 85.0
        elif euler < 200:
            score = 65.0
        else:
            score = 35.0

    # Sanity: mean thickness should be 1.5-4.0mm
    for key in ("mean_thickness_lh", "mean_thickness_rh"):
        val = features.get(key)
        if val is not None:
            if val < 1.0 or val > 5.0:
                score = min(score, 30.0)
            elif val < 1.5 or val > 4.0:
                score = min(score, 60.0)

    return score


def collect_all_features(freesurfer_dir: Path) -> dict[str, float]:
    """Collect all features from a FreeSurfer output directory."""
    stats_dir = freesurfer_dir / "stats"
    features: dict[str, float] = {}

    # Cortical thickness from aparc.stats
    for hemi in ("lh", "rh"):
        aparc = stats_dir / f"{hemi}.aparc.stats"
        features.update(parse_aparc_stats(aparc))

    # Subcortical volumes from aseg.stats
    aseg = stats_dir / "aseg.stats"
    features.update(parse_aseg_stats(aseg))

    # Compute global mean thickness
    lh = features.get("mean_thickness_lh")
    rh = features.get("mean_thickness_rh")
    if lh is not None and rh is not None:
        features["global_mean_thickness"] = (lh + rh) / 2.0

    return features
