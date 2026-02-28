"""Phase 6 — Fan-out / Fan-in orchestrator for technique module execution.

Manages parallel technique runs per analysis request:
  fan_out_techniques  — create TechniqueRun rows for each weighted technique
  on_technique_complete — mark one technique done, check if all finished
  fan_in_and_fuse — collect results and run fusion engine
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.technique import ServiceTechniqueWeight, TechniqueModule, TechniqueRun
from app.services.fusion_engine import FusionConfig, FusionResult, run_fusion
from app.services.technique_output import TechniqueOutput, validate_technique_output

logger = logging.getLogger(__name__)


async def fan_out_techniques(
    db: AsyncSession,
    run_id: uuid.UUID,
    service_id: uuid.UUID,
) -> list[TechniqueRun]:
    """Create a TechniqueRun for each active technique weighted on this service.

    Returns the list of created TechniqueRun objects.
    """
    # Fetch weights with technique info
    q = (
        select(ServiceTechniqueWeight, TechniqueModule)
        .join(TechniqueModule, ServiceTechniqueWeight.technique_module_id == TechniqueModule.id)
        .where(
            ServiceTechniqueWeight.service_id == service_id,
            TechniqueModule.status == "ACTIVE",
        )
        .order_by(ServiceTechniqueWeight.base_weight.desc())
    )
    rows = (await db.execute(q)).all()

    technique_runs = []
    for weight, technique in rows:
        job_spec = {
            "docker_image": technique.docker_image,
            "technique_key": technique.key,
            "modality": technique.modality,
            "base_weight": weight.base_weight,
            "resource_requirements": technique.resource_requirements or {},
        }

        tr = TechniqueRun(
            run_id=run_id,
            technique_module_id=technique.id,
            technique_key=technique.key,
            status="PENDING",
            job_spec=job_spec,
        )
        db.add(tr)
        technique_runs.append(tr)

    await db.flush()
    logger.info(
        "Fan-out: created %d technique runs for run %s (service %s)",
        len(technique_runs),
        run_id,
        service_id,
    )
    return technique_runs


async def on_technique_complete(
    db: AsyncSession,
    technique_run_id: uuid.UUID,
    output: TechniqueOutput,
) -> bool:
    """Mark a technique run as completed with output data.

    Returns True if ALL technique runs for the parent run are now done.
    """
    tr = (await db.execute(
        select(TechniqueRun).where(TechniqueRun.id == technique_run_id)
    )).scalar_one_or_none()
    if not tr:
        raise ValueError(f"TechniqueRun {technique_run_id} not found")

    tr.status = "COMPLETED"
    tr.output_data = output.to_dict()
    tr.qc_score = output.qc_score
    tr.completed_at = datetime.now(timezone.utc)
    await db.flush()

    # Check if all siblings are done
    siblings = (await db.execute(
        select(TechniqueRun).where(TechniqueRun.run_id == tr.run_id)
    )).scalars().all()

    return all(s.status in ("COMPLETED", "FAILED") for s in siblings)


async def mark_technique_failed(
    db: AsyncSession,
    technique_run_id: uuid.UUID,
    error_detail: str,
) -> bool:
    """Mark a technique run as failed. Returns True if all siblings are done."""
    tr = (await db.execute(
        select(TechniqueRun).where(TechniqueRun.id == technique_run_id)
    )).scalar_one_or_none()
    if not tr:
        raise ValueError(f"TechniqueRun {technique_run_id} not found")

    tr.status = "FAILED"
    tr.error_detail = error_detail
    tr.completed_at = datetime.now(timezone.utc)
    await db.flush()

    siblings = (await db.execute(
        select(TechniqueRun).where(TechniqueRun.run_id == tr.run_id)
    )).scalars().all()

    return all(s.status in ("COMPLETED", "FAILED") for s in siblings)


async def fan_in_and_fuse(
    db: AsyncSession,
    run_id: uuid.UUID,
    service_id: uuid.UUID,
) -> FusionResult:
    """Collect all completed technique outputs and run fusion.

    Raises ValueError if all techniques failed.
    """
    technique_runs = (await db.execute(
        select(TechniqueRun).where(TechniqueRun.run_id == run_id)
    )).scalars().all()

    # Collect completed outputs
    outputs: list[TechniqueOutput] = []
    for tr in technique_runs:
        if tr.status == "COMPLETED" and tr.output_data:
            try:
                out = validate_technique_output(tr.output_data, tr.technique_key)
                outputs.append(out)
            except ValueError as e:
                logger.warning("Invalid output for technique run %s: %s", tr.id, e)

    if not outputs:
        raise ValueError(f"All technique runs failed for run {run_id}")

    # Build weights from ServiceTechniqueWeight
    weights_q = (
        select(ServiceTechniqueWeight, TechniqueModule.key)
        .join(TechniqueModule, ServiceTechniqueWeight.technique_module_id == TechniqueModule.id)
        .where(ServiceTechniqueWeight.service_id == service_id)
    )
    weight_rows = (await db.execute(weights_q)).all()
    technique_weights = {key: w.base_weight for w, key in weight_rows}

    config = FusionConfig(
        service_id=str(service_id),
        technique_weights=technique_weights,
    )

    result = run_fusion(outputs, config)
    logger.info(
        "Fan-in: fusion complete for run %s — %d included, %d excluded, confidence=%.1f",
        run_id,
        len(result.included_modules),
        len(result.excluded_modules),
        result.confidence_score,
    )
    return result
