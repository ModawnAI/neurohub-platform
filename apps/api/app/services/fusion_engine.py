"""Phase 5 — QC-adjusted weighted fusion engine.

Implements the specification's fusion algorithm:
  w_adjusted = w_base × (qc_score / 100)
  Exclude modules with qc_score < qc_fail_threshold (default 40)
  Feature normalization via z-score
  Weighted aggregation: P(r) = Σ w_adjusted_i × S_i(r)
  Concordance = supporting_modalities / total_available
  Confidence = mean(qc_scores of included modules)
"""

from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass, field

from app.services.technique_output import TechniqueOutput

logger = logging.getLogger(__name__)


@dataclass
class FusionConfig:
    service_id: str
    technique_weights: dict[str, float]  # key → base_weight
    qc_fail_threshold: float = 40.0
    qc_warn_threshold: float = 60.0


@dataclass
class FusionResult:
    service_id: str
    fusion_engine: str = "neurohub_weighted_v1"
    fusion_version: str = "1.0.0"
    included_modules: list[str] = field(default_factory=list)
    excluded_modules: list[dict] = field(default_factory=list)
    qc_summary: dict = field(default_factory=dict)
    results: dict[str, float] = field(default_factory=dict)
    probability_maps: dict[str, str] = field(default_factory=dict)
    confidence_score: float = 0.0
    concordance_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def _z_score_normalize(values: list[float]) -> list[float]:
    """Z-score normalize a list of values. Returns zeros if std is 0."""
    if len(values) < 2:
        return [0.0] * len(values)
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance)
    if std == 0:
        return [0.0] * len(values)
    return [(v - mean) / std for v in values]


def run_fusion(
    outputs: list[TechniqueOutput],
    config: FusionConfig,
) -> FusionResult:
    """Run fusion across technique outputs with QC-adjusted weights.

    Raises ValueError if all modules are excluded.
    """
    if not outputs:
        raise ValueError("No technique outputs provided for fusion")

    # Check weight sum
    weight_sum = sum(config.technique_weights.values())
    if abs(weight_sum - 1.0) > 0.05:
        logger.warning(
            "Technique weights sum to %.3f (expected ≈1.0) for service %s",
            weight_sum,
            config.service_id,
        )

    # Step 1 & 2: QC weight adjustment + exclusion
    included: list[tuple[TechniqueOutput, float]] = []  # (output, w_adjusted)
    excluded: list[dict] = []

    for out in outputs:
        base_w = config.technique_weights.get(out.module, 0.0)
        if base_w == 0.0:
            excluded.append({"module": out.module, "reason": "no_weight_configured", "qc_score": out.qc_score})
            continue

        if out.qc_score < config.qc_fail_threshold:
            excluded.append({"module": out.module, "reason": "qc_below_threshold", "qc_score": out.qc_score})
            continue

        w_adjusted = base_w * (out.qc_score / 100.0)
        included.append((out, w_adjusted))

    if not included:
        raise ValueError(
            f"All {len(outputs)} modules excluded by QC threshold "
            f"({config.qc_fail_threshold}). Cannot produce fusion result."
        )

    # Step 3: Feature normalization (z-score per feature across modules)
    all_feature_keys: set[str] = set()
    for out, _ in included:
        all_feature_keys.update(out.features.keys())

    # Step 4: Weighted aggregation
    # Normalize weights to sum to 1.0 among included
    total_w = sum(w for _, w in included)
    aggregated: dict[str, float] = {}

    for feat_key in all_feature_keys:
        # Collect values for this feature from all included modules
        feat_values = []
        feat_weights = []
        for out, w in included:
            if feat_key in out.features:
                feat_values.append(out.features[feat_key])
                feat_weights.append(w)

        if not feat_values:
            continue

        # Z-score normalize
        z_values = _z_score_normalize(feat_values)
        # Weighted sum
        w_total = sum(feat_weights)
        if w_total > 0:
            aggregated[feat_key] = sum(z * w for z, w in zip(z_values, feat_weights)) / w_total

    # Merge probability maps from all included modules
    prob_maps: dict[str, str] = {}
    for out, _ in included:
        for map_name, map_path in out.maps.items():
            prob_maps[f"{out.module}__{map_name}"] = map_path

    # Step 5: Concordance = included / total available
    total_available = len(outputs)
    concordance = len(included) / total_available if total_available > 0 else 0.0

    # Step 6: Confidence = mean QC score of included modules
    included_qc = [out.qc_score for out, _ in included]
    confidence = sum(included_qc) / len(included_qc) if included_qc else 0.0

    # QC summary
    qc_summary = {
        "mean_qc": round(confidence, 2),
        "min_qc": round(min(included_qc), 2) if included_qc else 0.0,
        "max_qc": round(max(included_qc), 2) if included_qc else 0.0,
        "excluded_count": len(excluded),
        "included_count": len(included),
    }

    return FusionResult(
        service_id=config.service_id,
        included_modules=[out.module for out, _ in included],
        excluded_modules=excluded,
        qc_summary=qc_summary,
        results={k: round(v, 6) for k, v in aggregated.items()},
        probability_maps=prob_maps,
        confidence_score=round(confidence, 2),
        concordance_score=round(concordance, 4),
    )
