"""Pipeline Orchestrator — end-to-end processing from zip upload to results.

Coordinates the full analysis pipeline:
  1. Download zip from storage
  2. Extract + smart-scan for DICOM/NIfTI files
  3. DICOM → NIfTI conversion (dcm2niix)
  4. Modality classification + best-volume selection
  5. BIDS organization
  6. Pre-QC validation
  7. Technique fan-out + container execution
  8. Fusion + report generation

This module is called from Celery tasks and operates synchronously
(using asyncio.run where needed for async services).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("neurohub.pipeline_orchestrator")


@dataclass
class PipelineStageResult:
    """Result of a single pipeline stage."""

    stage: str
    status: str  # COMPLETED, FAILED, SKIPPED
    duration_ms: int = 0
    details: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class PipelineResult:
    """Full pipeline execution result."""

    request_id: str
    case_id: str
    status: str  # COMPLETED, PARTIAL, FAILED
    stages: list[PipelineStageResult] = field(default_factory=list)
    bids_dir: str | None = None
    modalities_found: list[str] = field(default_factory=list)
    pre_qc_checks: list[dict] = field(default_factory=list)
    can_proceed: bool = False
    technique_runs: list[dict] = field(default_factory=list)
    fusion_result: dict | None = None
    report_path: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "case_id": self.case_id,
            "status": self.status,
            "stages": [
                {
                    "stage": s.stage,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "details": s.details,
                    "error": s.error,
                }
                for s in self.stages
            ],
            "bids_dir": self.bids_dir,
            "modalities_found": self.modalities_found,
            "pre_qc_summary": {
                "total_checks": len(self.pre_qc_checks),
                "pass": sum(1 for c in self.pre_qc_checks if c.get("status") == "PASS"),
                "warn": sum(1 for c in self.pre_qc_checks if c.get("status") == "WARN"),
                "fail": sum(1 for c in self.pre_qc_checks if c.get("status") == "FAIL"),
                "can_proceed": self.can_proceed,
            },
            "technique_runs": self.technique_runs,
            "fusion_result": self.fusion_result,
            "report_path": self.report_path,
            "errors": self.errors,
        }


def _timed(func):
    """Decorator to time a stage and return PipelineStageResult."""
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            result = func(*args, **kwargs)
            duration = int((time.monotonic() - start) * 1000)
            if isinstance(result, PipelineStageResult):
                result.duration_ms = duration
                return result
            return PipelineStageResult(
                stage=func.__name__,
                status="COMPLETED",
                duration_ms=duration,
                details=result if isinstance(result, dict) else {},
            )
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            logger.exception("Stage %s failed: %s", func.__name__, e)
            return PipelineStageResult(
                stage=func.__name__,
                status="FAILED",
                duration_ms=duration,
                error=str(e),
            )

    return wrapper


class PipelineOrchestrator:
    """Orchestrates the full analysis pipeline for a single case."""

    def __init__(
        self,
        work_dir: str,
        request_id: str,
        case_id: str,
        service_id: str | None = None,
        patient_ref: str = "unknown",
    ):
        self.work_dir = work_dir
        self.request_id = request_id
        self.case_id = case_id
        self.service_id = service_id
        self.patient_ref = patient_ref

        # Working directories
        self.extract_dir = os.path.join(work_dir, "extracted")
        self.nifti_dir = os.path.join(work_dir, "nifti")
        self.bids_dir = os.path.join(work_dir, "bids")
        self.output_dir = os.path.join(work_dir, "outputs")

        os.makedirs(self.nifti_dir, exist_ok=True)
        os.makedirs(self.bids_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        self.result = PipelineResult(
            request_id=request_id,
            case_id=case_id,
            status="RUNNING",
        )

    def run_full_pipeline(self, zip_path: str) -> PipelineResult:
        """Execute the full pipeline from zip file to results.

        Args:
            zip_path: Path to the uploaded zip file on local disk.

        Returns:
            PipelineResult with all stage outcomes.
        """
        logger.info(
            "Starting pipeline for request=%s case=%s zip=%s",
            self.request_id, self.case_id, zip_path,
        )

        # Stage 1: Extract + Scan
        scan_result = self._stage_extract_and_scan(zip_path)
        self.result.stages.append(scan_result)
        if scan_result.status == "FAILED":
            self.result.status = "FAILED"
            self.result.errors.append(f"Extract/scan failed: {scan_result.error}")
            return self.result

        # Stage 2: DICOM → NIfTI conversion
        volumes_result = self._stage_convert_to_nifti(scan_result)
        self.result.stages.append(volumes_result)
        if volumes_result.status == "FAILED":
            self.result.status = "FAILED"
            self.result.errors.append(f"Conversion failed: {volumes_result.error}")
            return self.result

        # Stage 3: Modality classification + best selection
        selection_result = self._stage_select_best_volumes()
        self.result.stages.append(selection_result)
        if selection_result.status == "FAILED":
            self.result.status = "FAILED"
            self.result.errors.append(f"Selection failed: {selection_result.error}")
            return self.result

        # Stage 4: BIDS organization
        bids_result = self._stage_organize_bids()
        self.result.stages.append(bids_result)
        if bids_result.status == "FAILED":
            self.result.status = "FAILED"
            self.result.errors.append(f"BIDS organization failed: {bids_result.error}")
            return self.result

        # Stage 5: Pre-QC checks
        qc_result = self._stage_pre_qc()
        self.result.stages.append(qc_result)
        # Pre-QC failures don't stop the pipeline — they're advisory

        # Stage 6: Technique execution (if Pre-QC passes or overridden)
        if self.result.can_proceed:
            technique_result = self._stage_execute_techniques()
        else:
            technique_result = PipelineStageResult(
                stage="execute_techniques",
                status="SKIPPED",
                details={"reason": "Pre-QC has FAIL checks"},
            )
        self.result.stages.append(technique_result)

        # Determine final status
        has_fails = any(s.status == "FAILED" for s in self.result.stages)
        has_technique_results = any(
            t.get("status") == "COMPLETED" for t in self.result.technique_runs
        )

        if has_technique_results:
            self.result.status = "COMPLETED"
        elif not has_fails:
            self.result.status = "PARTIAL"  # Pre-QC blocked techniques
        else:
            self.result.status = "FAILED"

        logger.info(
            "Pipeline complete: status=%s, stages=%d, modalities=%s",
            self.result.status,
            len(self.result.stages),
            self.result.modalities_found,
        )
        return self.result

    @_timed
    def _stage_extract_and_scan(self, zip_path: str) -> PipelineStageResult:
        """Stage 1: Extract zip and scan for medical imaging files."""
        from app.services.zip_processor import extract_and_scan

        scan = _run_async(extract_and_scan(zip_path, self.work_dir))

        # Store scan result for next stages
        self._scan_result = scan

        if not scan.has_dicom and not scan.has_nifti:
            return PipelineStageResult(
                stage="extract_and_scan",
                status="FAILED",
                error="Zip 파일에서 DICOM 또는 NIfTI 파일을 찾을 수 없습니다. "
                      "의료 영상 파일이 포함된 zip 파일을 업로드해 주세요.",
                details=scan.summary(),
            )

        self.result.modalities_found = sorted(scan.modalities_found)

        return PipelineStageResult(
            stage="extract_and_scan",
            status="COMPLETED",
            details=scan.summary(),
        )

    @_timed
    def _stage_convert_to_nifti(self, _prev_result) -> PipelineStageResult:
        """Stage 2: Convert DICOM to NIfTI using dcm2niix."""
        scan = self._scan_result

        # If we already have NIfTI files, use those directly
        if scan.has_nifti and not scan.has_dicom:
            self._nifti_volumes = []
            for nf in scan.nifti_files:
                from app.services.bids_converter import NiftiVolume, classify_modality
                sidecar = {}
                if nf.json_sidecar:
                    import json as json_mod
                    with open(nf.json_sidecar) as f:
                        sidecar = json_mod.load(f)
                shape = _get_nifti_shape(nf.path)
                modality = classify_modality(sidecar) if sidecar else "UNKNOWN"
                self._nifti_volumes.append(NiftiVolume(
                    nifti_path=nf.path,
                    json_sidecar=sidecar,
                    shape=shape,
                    modality_tag=modality,
                ))
            return PipelineStageResult(
                stage="convert_to_nifti",
                status="COMPLETED",
                details={
                    "source": "existing_nifti",
                    "volume_count": len(self._nifti_volumes),
                },
            )

        # Organize DICOM files for dcm2niix
        from app.services.zip_processor import prepare_dicom_input_dir

        organized_dir = prepare_dicom_input_dir(scan, self.work_dir)

        # Run dcm2niix on each series directory
        from app.services.bids_converter import convert_dicom_to_nifti

        all_volumes = []
        series_dirs = [
            os.path.join(organized_dir, d)
            for d in os.listdir(organized_dir)
            if os.path.isdir(os.path.join(organized_dir, d))
        ]

        for series_dir in series_dirs:
            try:
                volumes = _run_async(
                    convert_dicom_to_nifti(series_dir, self.nifti_dir)
                )
                all_volumes.extend(volumes)
            except Exception as e:
                logger.warning("dcm2niix failed for %s: %s", series_dir, e)

        # Also include any NIfTI files found in the zip
        if scan.has_nifti:
            from app.services.bids_converter import NiftiVolume, classify_modality
            for nf in scan.nifti_files:
                sidecar = {}
                if nf.json_sidecar:
                    with open(nf.json_sidecar) as f:
                        sidecar = json.load(f)
                shape = _get_nifti_shape(nf.path)
                modality = classify_modality(sidecar) if sidecar else "UNKNOWN"
                all_volumes.append(NiftiVolume(
                    nifti_path=nf.path,
                    json_sidecar=sidecar,
                    shape=shape,
                    modality_tag=modality,
                ))

        self._nifti_volumes = all_volumes

        if not all_volumes:
            return PipelineStageResult(
                stage="convert_to_nifti",
                status="FAILED",
                error="DICOM → NIfTI 변환에 실패했습니다. DICOM 파일이 손상되었을 수 있습니다.",
            )

        # Update modalities from converted volumes
        mods = {v.modality_tag for v in all_volumes if v.modality_tag != "UNKNOWN"}
        self.result.modalities_found = sorted(mods)

        return PipelineStageResult(
            stage="convert_to_nifti",
            status="COMPLETED",
            details={
                "source": "dcm2niix",
                "volume_count": len(all_volumes),
                "modalities": sorted(mods),
            },
        )

    @_timed
    def _stage_select_best_volumes(self) -> PipelineStageResult:
        """Stage 3: Select best volume per modality."""
        from app.services.bids_converter import select_best_per_modality

        self._selected = select_best_per_modality(self._nifti_volumes)

        if not self._selected:
            return PipelineStageResult(
                stage="select_best_volumes",
                status="FAILED",
                error="품질 기준을 충족하는 영상이 없습니다.",
            )

        return PipelineStageResult(
            stage="select_best_volumes",
            status="COMPLETED",
            details={
                "selected_modalities": list(self._selected.keys()),
                "selected_files": {
                    mod: os.path.basename(vol.nifti_path)
                    for mod, vol in self._selected.items()
                },
            },
        )

    @_timed
    def _stage_organize_bids(self) -> PipelineStageResult:
        """Stage 4: Organize into BIDS directory structure."""
        from app.services.bids_converter import organize_bids

        subject_id = self.patient_ref.replace(" ", "").replace("-", "")[:16] or "001"

        bids_root = _run_async(
            organize_bids(
                self._selected,
                subject_id=subject_id,
                output_dir=self.bids_dir,
            )
        )
        self.result.bids_dir = bids_root

        return PipelineStageResult(
            stage="organize_bids",
            status="COMPLETED",
            details={
                "bids_dir": bids_root,
                "subject_id": subject_id,
            },
        )

    @_timed
    def _stage_pre_qc(self) -> PipelineStageResult:
        """Stage 5: Run Pre-QC checks on selected volumes."""
        from app.services.pre_qc import check_minimum_requirements

        all_checks = []
        for mod, vol in self._selected.items():
            checks = check_minimum_requirements(
                json_sidecar=vol.json_sidecar,
                nifti_shape=vol.shape,
                modality=mod,
                nifti_path=vol.nifti_path,
            )
            for c in checks:
                all_checks.append({
                    "modality": c.modality,
                    "check_type": c.check_type,
                    "status": c.status,
                    "score": c.score,
                    "message_ko": c.message_ko,
                    "message_en": c.message_en,
                })

        self.result.pre_qc_checks = all_checks
        has_fail = any(c["status"] == "FAIL" for c in all_checks)
        self.result.can_proceed = not has_fail

        return PipelineStageResult(
            stage="pre_qc",
            status="COMPLETED",
            details={
                "total_checks": len(all_checks),
                "pass": sum(1 for c in all_checks if c["status"] == "PASS"),
                "warn": sum(1 for c in all_checks if c["status"] == "WARN"),
                "fail": sum(1 for c in all_checks if c["status"] == "FAIL"),
                "can_proceed": self.result.can_proceed,
            },
        )

    @_timed
    def _stage_execute_techniques(self) -> PipelineStageResult:
        """Stage 6: Execute technique containers via LocalContainerRunner."""
        from app.config import settings as _settings

        if not _settings.local_docker_enabled:
            return PipelineStageResult(
                stage="execute_techniques",
                status="SKIPPED",
                details={"reason": "local_docker_enabled=false"},
            )

        if not self.service_id:
            return PipelineStageResult(
                stage="execute_techniques",
                status="SKIPPED",
                details={"reason": "no_service_id"},
            )

        # Get technique modules for this service
        from app.database import sync_session_factory
        from app.models.technique import ServiceTechniqueWeight, TechniqueModule
        from sqlalchemy import select

        with sync_session_factory() as session:
            q = (
                select(ServiceTechniqueWeight, TechniqueModule)
                .join(
                    TechniqueModule,
                    ServiceTechniqueWeight.technique_module_id == TechniqueModule.id,
                )
                .where(
                    ServiceTechniqueWeight.service_id == uuid.UUID(self.service_id),
                    TechniqueModule.status == "ACTIVE",
                )
            )
            rows = session.execute(q).all()

        if not rows:
            return PipelineStageResult(
                stage="execute_techniques",
                status="SKIPPED",
                details={"reason": "no_techniques_for_service"},
            )

        # Filter techniques to those whose modality we actually have
        available_modalities = set(self._selected.keys())
        applicable = []
        for weight, technique in rows:
            tech_modality = technique.modality
            # Map technique modality to our modality names
            if tech_modality in available_modalities or tech_modality == "MULTI":
                applicable.append((weight, technique))

        if not applicable:
            return PipelineStageResult(
                stage="execute_techniques",
                status="SKIPPED",
                details={
                    "reason": "no_applicable_techniques",
                    "available_modalities": sorted(available_modalities),
                    "technique_modalities": [t.modality for _, t in rows],
                },
            )

        # Execute each technique container
        from app.services.local_container_runner import LocalContainerRunner

        runner = LocalContainerRunner()
        technique_results = []

        for weight, technique in applicable:
            technique_output_dir = os.path.join(
                self.output_dir, technique.key
            )
            os.makedirs(technique_output_dir, exist_ok=True)

            logger.info(
                "Executing technique %s (image=%s, weight=%.2f)",
                technique.key, technique.docker_image, weight.base_weight,
            )

            try:
                result = _run_async(
                    runner.execute_technique(
                        technique_key=technique.key,
                        docker_image=technique.docker_image,
                        input_dir=self.result.bids_dir or self.bids_dir,
                        output_dir=technique_output_dir,
                        job_spec={
                            "technique_key": technique.key,
                            "modality": technique.modality,
                            "base_weight": weight.base_weight,
                        },
                        timeout=technique.resource_requirements.get("timeout", 7200)
                        if technique.resource_requirements else 7200,
                        gpu=technique.resource_requirements.get("gpu", False)
                        if technique.resource_requirements else False,
                    )
                )

                technique_results.append({
                    "technique_key": technique.key,
                    "docker_image": technique.docker_image,
                    "status": "COMPLETED" if result.exit_code == 0 else "FAILED",
                    "exit_code": result.exit_code,
                    "duration_ms": result.duration_ms,
                    "output": result.technique_output,
                    "qc_score": (result.technique_output or {}).get("qc_score"),
                    "base_weight": weight.base_weight,
                })

            except Exception as e:
                logger.exception("Technique %s failed: %s", technique.key, e)
                technique_results.append({
                    "technique_key": technique.key,
                    "docker_image": technique.docker_image,
                    "status": "FAILED",
                    "exit_code": -1,
                    "error": str(e),
                    "base_weight": weight.base_weight,
                })

        self.result.technique_runs = technique_results

        # Run fusion if we have completed techniques
        completed = [t for t in technique_results if t["status"] == "COMPLETED" and t.get("output")]
        if completed:
            fusion = self._run_fusion(completed)
            if fusion:
                self.result.fusion_result = fusion

        completed_count = sum(1 for t in technique_results if t["status"] == "COMPLETED")
        failed_count = sum(1 for t in technique_results if t["status"] == "FAILED")

        return PipelineStageResult(
            stage="execute_techniques",
            status="COMPLETED" if completed_count > 0 else "FAILED",
            details={
                "total": len(technique_results),
                "completed": completed_count,
                "failed": failed_count,
            },
        )

    def _run_fusion(self, completed_techniques: list[dict]) -> dict | None:
        """Run fusion engine on completed technique outputs."""
        try:
            from app.services.fusion_engine import FusionConfig, run_fusion
            from app.services.technique_output import validate_technique_output

            outputs = []
            technique_weights = {}

            for t in completed_techniques:
                try:
                    out = validate_technique_output(t["output"], t["technique_key"])
                    outputs.append(out)
                    technique_weights[t["technique_key"]] = t.get("base_weight", 0.5)
                except ValueError as e:
                    logger.warning("Invalid technique output for %s: %s", t["technique_key"], e)

            if not outputs:
                return None

            config = FusionConfig(
                service_id=self.service_id or "",
                technique_weights=technique_weights,
            )
            result = run_fusion(outputs, config)
            return result.to_dict()

        except Exception as e:
            logger.exception("Fusion failed: %s", e)
            return None


def _run_async(coro):
    """Run an async coroutine from sync context (Celery worker)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already in async context — run in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


def _get_nifti_shape(nifti_path: str) -> tuple[int, ...]:
    """Get NIfTI volume shape."""
    try:
        import nibabel as nib
        img = nib.load(nifti_path)
        return tuple(img.shape)
    except Exception:
        return ()
