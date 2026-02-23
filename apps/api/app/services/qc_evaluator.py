"""QC Evaluator: evaluates pipeline results against QC rules and decides next state.

Called after a run completes successfully to determine whether the request
should auto-advance to REPORTING or pause at QC for manual review.
"""

import logging
from typing import Any

from app.services.state_machine import RequestStatus

logger = logging.getLogger("neurohub.qc_evaluator")


def evaluate_qc(
    result_manifest: dict[str, Any] | None,
    qc_rules: dict[str, Any] | None,
) -> RequestStatus:
    """Evaluate QC rules against a result manifest and decide the next Request state.

    Args:
        result_manifest: The output from the compute worker (Run.result_manifest).
        qc_rules: The QC rules from pipeline_snapshot.qc_rules.

    Returns:
        RequestStatus.REPORTING if auto-approved (high confidence, auto_approve enabled).
        RequestStatus.QC if manual review is needed.
    """
    if not result_manifest or not qc_rules:
        logger.info("No QC rules or result manifest; defaulting to QC state")
        return RequestStatus.QC

    # Check if expert review is always required
    if qc_rules.get("require_expert_review", False):
        logger.info("Expert review required by QC rules")
        return RequestStatus.QC

    # Check output completeness
    required_outputs = qc_rules.get("required_outputs", [])
    output_artifacts = result_manifest.get("output_artifacts", {})
    if required_outputs:
        missing = [o for o in required_outputs if o not in output_artifacts]
        if missing:
            logger.info("Missing required outputs: %s; routing to QC", missing)
            return RequestStatus.QC

    # Check value ranges
    value_ranges = qc_rules.get("value_ranges", {})
    metrics = result_manifest.get("metrics", {})
    for key, bounds in value_ranges.items():
        value = metrics.get(key)
        if value is None:
            logger.info("Missing metric '%s'; routing to QC", key)
            return RequestStatus.QC
        min_val = bounds.get("min")
        max_val = bounds.get("max")
        if min_val is not None and value < min_val:
            logger.info("Metric '%s'=%s below min %s; routing to QC", key, value, min_val)
            return RequestStatus.QC
        if max_val is not None and value > max_val:
            logger.info("Metric '%s'=%s above max %s; routing to QC", key, value, max_val)
            return RequestStatus.QC

    # Check confidence score
    auto_approve = qc_rules.get("auto_approve", False)
    confidence = result_manifest.get("confidence_score")
    threshold = qc_rules.get("confidence_threshold", 0.9)

    if confidence is None:
        logger.info("No confidence score in result manifest; routing to QC")
        return RequestStatus.QC

    if auto_approve and confidence >= threshold:
        logger.info(
            "Auto-approved: confidence=%.3f >= threshold=%.3f",
            confidence,
            threshold,
        )
        return RequestStatus.REPORTING

    logger.info(
        "Routing to QC: confidence=%.3f, threshold=%.3f, auto_approve=%s",
        confidence,
        threshold,
        auto_approve,
    )
    return RequestStatus.QC
