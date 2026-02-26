"""Group analysis service — statistical aggregation across multiple patient runs."""
import math
import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group_analysis import GroupStudy, GroupStudyMember
from app.models.run import Run


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    m = sum(values) / len(values)
    variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _cohens_d(group_a: list[float], group_b: list[float]) -> float | None:
    if not group_a or not group_b:
        return None
    mean_a = sum(group_a) / len(group_a)
    mean_b = sum(group_b) / len(group_b)
    n_a, n_b = len(group_a), len(group_b)
    if n_a + n_b - 2 <= 0:
        return None
    pooled_std = math.sqrt(
        ((n_a - 1) * (_std(group_a) or 0) ** 2 + (n_b - 1) * (_std(group_b) or 0) ** 2)
        / (n_a + n_b - 2)
    )
    if pooled_std == 0:
        return None
    return (mean_a - mean_b) / pooled_std


def _t_statistic(group_a: list[float], group_b: list[float]) -> tuple[float | None, float | None]:
    """Welch's t-test approximation, returns (t, p_approx)."""
    if len(group_a) < 2 or len(group_b) < 2:
        return None, None
    mean_a = sum(group_a) / len(group_a)
    mean_b = sum(group_b) / len(group_b)
    var_a = (_std(group_a) or 0) ** 2
    var_b = (_std(group_b) or 0) ** 2
    n_a, n_b = len(group_a), len(group_b)
    denom = math.sqrt(var_a / n_a + var_b / n_b)
    if denom == 0:
        return None, None
    t = (mean_a - mean_b) / denom
    # Very rough p-value approximation via normal approximation (no scipy available)
    # |t| > 1.96 → p < 0.05, |t| > 2.576 → p < 0.01
    abs_t = abs(t)
    if abs_t >= 3.0:
        p_approx = 0.003
    elif abs_t >= 2.576:
        p_approx = 0.01
    elif abs_t >= 1.96:
        p_approx = 0.05
    elif abs_t >= 1.645:
        p_approx = 0.10
    else:
        p_approx = 0.50
    return t, p_approx


def _extract_numeric_metrics(result_manifest: dict | None) -> dict[str, float]:
    """Recursively extract scalar numeric values from a result manifest."""
    if not result_manifest:
        return {}
    metrics: dict[str, float] = {}

    def _recurse(obj: Any, prefix: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = f"{prefix}.{k}" if prefix else k
                _recurse(v, key)
        elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
            metrics[prefix] = float(obj)

    _recurse(result_manifest)
    return metrics


async def run_group_analysis(study_id: uuid.UUID, db: AsyncSession) -> GroupStudy:
    """Run statistical group analysis and store results on the study."""
    study_result = await db.execute(
        select(GroupStudy).where(GroupStudy.id == study_id)
    )
    study = study_result.scalar_one_or_none()
    if not study:
        raise ValueError(f"GroupStudy {study_id} not found")

    study.status = "RUNNING"
    await db.flush()

    try:
        # Load members
        members_result = await db.execute(
            select(GroupStudyMember).where(GroupStudyMember.study_id == study_id)
        )
        members = list(members_result.scalars())

        if len(members) < 2:
            raise ValueError("Need at least 2 members to run analysis")

        # Collect runs for each member request
        # group_label → list of numeric metrics
        group_data: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

        for member in members:
            runs_result = await db.execute(
                select(Run).where(
                    Run.request_id == member.request_id,
                    Run.status == "COMPLETED",
                )
            )
            runs = list(runs_result.scalars())
            for run in runs:
                extracted = _extract_numeric_metrics(run.result_manifest)
                for metric_key, value in extracted.items():
                    group_data[member.group_label][metric_key].append(value)

        # Build groups output
        all_metric_keys: set[str] = set()
        for gd in group_data.values():
            all_metric_keys.update(gd.keys())

        groups_out = []
        for label, metrics in group_data.items():
            metric_summary = {}
            for key in all_metric_keys:
                vals = metrics.get(key, [])
                metric_summary[key] = {
                    "mean": _mean(vals),
                    "std": _std(vals),
                    "n": len(vals),
                }
            groups_out.append({
                "label": label,
                "n": max((len(v) for v in metrics.values()), default=0),
                "metrics": metric_summary,
            })

        # Statistical tests (for COMPARISON: pairwise t-tests)
        stat_tests = []
        group_labels = list(group_data.keys())

        if study.analysis_type in ("COMPARISON", "CORRELATION"):
            for metric_key in all_metric_keys:
                for i in range(len(group_labels)):
                    for j in range(i + 1, len(group_labels)):
                        la, lb = group_labels[i], group_labels[j]
                        vals_a = group_data[la].get(metric_key, [])
                        vals_b = group_data[lb].get(metric_key, [])
                        t, p = _t_statistic(vals_a, vals_b)
                        d = _cohens_d(vals_a, vals_b)
                        stat_tests.append({
                            "name": f"t-test: {metric_key} ({la} vs {lb})",
                            "p_value": p,
                            "effect_size": d,
                            "statistic": t,
                        })

        # Summary
        total_members = len(members)
        n_groups = len(group_data)
        summary = {
            "total_members": total_members,
            "n_groups": n_groups,
            "group_labels": group_labels,
            "metrics_analyzed": list(all_metric_keys),
            "analysis_type": study.analysis_type,
        }

        study.result = {
            "summary": summary,
            "groups": groups_out,
            "statistical_tests": stat_tests,
        }
        study.status = "COMPLETED"

    except Exception as exc:
        study.status = "FAILED"
        study.result = {"error": str(exc)}
        raise

    await db.flush()
    return study
