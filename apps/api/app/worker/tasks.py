"""Celery tasks for run execution and report generation.

These tasks are dispatched by the outbox reconciler and execute
the compute pipeline (simulated for now) and report generation.
"""

import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import sync_session_factory
from app.models.notification import Notification
from app.models.outbox import OutboxEvent
from app.models.report import Report
from app.models.request import Request
from app.models.run import Run
from app.worker.celery_app import celery_app

logger = logging.getLogger("neurohub.worker")


def _create_sync_notification(
    session,
    institution_id,
    user_id,
    event_type: str,
    title: str,
    body: str | None = None,
    entity_type: str | None = None,
    entity_id=None,
    metadata: dict | None = None,
) -> None:
    """Create a notification in sync session context (for Celery tasks)."""
    if not user_id:
        return
    session.add(
        Notification(
            institution_id=institution_id,
            user_id=user_id,
            event_type=event_type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_=metadata or {},
        )
    )


def _notify_service_evaluators(
    session,
    service_id,
    institution_id,
    event_type: str,
    title: str,
    body: str | None = None,
    entity_type: str | None = None,
    entity_id=None,
) -> None:
    """Notify all active evaluators assigned to a service."""
    from app.models.evaluation import ServiceEvaluator

    evaluators = (
        session.execute(
            select(ServiceEvaluator).where(
                ServiceEvaluator.service_id == service_id,
                ServiceEvaluator.institution_id == institution_id,
                ServiceEvaluator.is_active == True,  # noqa: E712
            )
        )
        .scalars()
        .all()
    )
    for ev in evaluators:
        _create_sync_notification(
            session,
            institution_id=institution_id,
            user_id=ev.user_id,
            event_type=event_type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    logger.info(
        "Notified %d evaluators for service %s (event: %s)",
        len(evaluators), service_id, event_type,
    )



# ── Webhook Delivery Task ─────────────────────────────────────────────────


@celery_app.task(
    name="neurohub.tasks.deliver_webhook",
    bind=True,
    max_retries=5,
    default_retry_delay=10,
    queue="reporting",
)
def deliver_webhook(self, webhook_id: str, event_type: str, data: dict):
    """Deliver a webhook with exponential backoff and delivery logging."""
    import json

    import httpx

    from app.models.webhook import Webhook, WebhookDeliveryLog
    from app.services.webhook_service import build_webhook_payload, generate_webhook_signature

    logger.info(
        "Delivering webhook %s event=%s (attempt %d)",
        webhook_id,
        event_type,
        self.request.retries + 1,
    )

    with sync_session_factory() as session:
        webhook = session.execute(
            select(Webhook).where(Webhook.id == uuid.UUID(webhook_id))
        ).scalar_one_or_none()

        if not webhook or webhook.status not in ("ACTIVE",):
            logger.warning("Webhook %s not active, skipping", webhook_id)
            return {"webhook_id": webhook_id, "status": "SKIPPED"}

        payload = build_webhook_payload(event_type, data)
        payload_str = json.dumps(payload, default=str)
        signature = generate_webhook_signature(payload_str, webhook.secret_hash)

        headers = {
            "Content-Type": "application/json",
            "X-NeuroHub-Signature": signature,
            "X-NeuroHub-Event": event_type,
            "X-NeuroHub-Delivery": str(uuid.uuid4()),
        }

        status_code = None
        response_body = None
        success = False
        error_detail = None

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(webhook.url, content=payload_str, headers=headers)
                status_code = resp.status_code
                response_body = resp.text[:2000]
                success = resp.status_code < 300
        except Exception as e:
            error_detail = str(e)[:2000]

        # Log delivery
        session.add(
            WebhookDeliveryLog(
                webhook_id=webhook.id,
                event_type=event_type,
                payload=payload,
                status_code=status_code,
                response_body=response_body,
                success=success,
                attempt=self.request.retries + 1,
                error_detail=error_detail,
            )
        )

        if success:
            webhook.last_delivered_at = datetime.now(timezone.utc)
            webhook.failure_count = 0
            session.commit()
            return {"webhook_id": webhook_id, "status": "DELIVERED"}
        else:
            webhook.failure_count = (webhook.failure_count or 0) + 1
            # Auto-disable after 10 consecutive failures
            if webhook.failure_count >= 10:
                webhook.status = "PAUSED"
                logger.warning(
                    "Webhook %s paused after %d failures", webhook_id, webhook.failure_count
                )
            session.commit()

            # Exponential backoff: 10s, 20s, 40s, 80s, 160s
            raise self.retry(
                countdown=10 * (2**self.request.retries),
                exc=Exception(error_detail or f"HTTP {status_code}"),
            )


# ── PDF Report Generation Task ────────────────────────────────────────────


@celery_app.task(
    name="neurohub.tasks.generate_pdf_report",
    bind=True,
    max_retries=2,
    default_retry_delay=15,
    queue="reporting",
)
def generate_pdf_report(self, request_id: str):
    """Generate a PDF report and upload to Supabase Storage."""
    from app.models.qc_decision import QCDecision
    from app.services.pdf_report import generate_report_html, render_pdf, upload_pdf_to_storage

    logger.info("Generating PDF report for request: %s", request_id)

    with sync_session_factory() as session:
        request = session.execute(
            select(Request).where(Request.id == uuid.UUID(request_id))
        ).scalar_one_or_none()

        if not request:
            logger.error("Request %s not found", request_id)
            return {"request_id": request_id, "status": "NOT_FOUND"}

        # Get report record
        report = session.execute(
            select(Report)
            .where(Report.request_id == uuid.UUID(request_id))
            .order_by(Report.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if not report:
            logger.error("No report record found for request %s", request_id)
            return {"request_id": request_id, "status": "NO_REPORT"}

        # Gather data for PDF
        runs = (
            session.execute(select(Run).where(Run.request_id == uuid.UUID(request_id)))
            .scalars()
            .all()
        )

        qc_decisions = (
            session.execute(
                select(QCDecision)
                .where(QCDecision.request_id == uuid.UUID(request_id))
                .order_by(QCDecision.created_at.desc())
            )
            .scalars()
            .all()
        )

        from app.models.report import ReportReview

        reviews = (
            session.execute(
                select(ReportReview)
                .where(ReportReview.report_id == report.id)
                .order_by(ReportReview.created_at.desc())
            )
            .scalars()
            .all()
        )

        cases_data = []
        if request.cases:
            cases_data = [
                {
                    "patient_ref": c.patient_ref,
                    "status": c.status,
                    "demographics": c.demographics or {},
                }
                for c in request.cases
            ]

        runs_data = [
            {
                "run_id": str(r.id),
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ]

        qc_data = [
            {
                "decision": q.decision,
                "qc_score": q.qc_score,
                "comments": q.comments,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in qc_decisions
        ]

        review_data = [
            {
                "decision": rv.decision,
                "severity": rv.severity,
                "category": rv.category,
                "comments": rv.comments,
                "created_at": rv.created_at.isoformat() if rv.created_at else None,
            }
            for rv in reviews
        ]

        service_name = (request.service_snapshot or {}).get("display_name", "N/A")

        html = generate_report_html(
            title=report.title or f"분석 보고서 - {service_name}",
            request_id=str(request.id),
            service_name=service_name,
            status=request.status,
            summary=report.summary or "보고서 요약 없음",
            cases=cases_data,
            runs=runs_data,
            qc_decisions=qc_data,
            reviews=review_data,
        )

        try:
            pdf_bytes = render_pdf(html)
            storage_path = upload_pdf_to_storage(
                pdf_bytes,
                institution_id=str(request.institution_id),
                request_id=str(request.id),
                report_id=str(report.id),
            )
            report.pdf_storage_path = storage_path
            session.commit()
            logger.info("PDF report generated and uploaded for request %s", request_id)
            return {"request_id": request_id, "status": "COMPLETED", "storage_path": storage_path}
        except Exception as exc:
            logger.exception("PDF generation failed for request %s: %s", request_id, exc)
            report.error_detail = str(exc)[:2000]
            session.commit()
            raise self.retry(exc=exc)


# ── Watermark Task ────────────────────────────────────────────────────────


def _download_from_storage(bucket: str, path: str) -> bytes:
    from app.services.storage import get_object_sync

    return get_object_sync(bucket, path)


def _upload_to_storage(bucket: str, path: str, data: bytes, content_type: str) -> str:
    from app.services.storage import put_object_sync

    put_object_sync(bucket, path, data, content_type=content_type)
    return path


@celery_app.task(
    name="neurohub.tasks.apply_watermark",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    queue="compute",
)
def apply_watermark_task(self, request_id: str, evaluation_id: str):
    """Download input image, apply watermark, upload result, trigger report."""
    from app.config import settings
    from app.models.evaluation import Evaluation
    from app.models.request import CaseFile
    from app.worker.watermark import apply_watermark

    logger.info("Starting watermark task for request=%s evaluation=%s", request_id, evaluation_id)

    with sync_session_factory() as session:
        evaluation = session.execute(
            select(Evaluation).where(Evaluation.id == uuid.UUID(evaluation_id))
        ).scalar_one_or_none()
        if not evaluation:
            logger.error("Evaluation %s not found", evaluation_id)
            return {"status": "NOT_FOUND"}

        request = session.execute(
            select(Request).where(Request.id == uuid.UUID(request_id))
        ).scalar_one_or_none()
        if not request:
            logger.error("Request %s not found", request_id)
            return {"status": "NOT_FOUND"}

        # Find first image file from cases
        case_ids = [c.id for c in request.cases] if request.cases else []
        image_file = None
        if case_ids:
            files = (
                session.execute(
                    select(CaseFile).where(CaseFile.case_id.in_(case_ids))
                )
                .scalars()
                .all()
            )
            for f in files:
                if f.file_name and any(
                    f.file_name.lower().endswith(ext)
                    for ext in (".jpg", ".jpeg", ".png")
                ):
                    image_file = f
                    break
            if not image_file and files:
                image_file = files[0]

        if not image_file or not image_file.storage_path:
            logger.warning("No image file found for request %s", request_id)
            # Still proceed to report generation
            session.add(
                OutboxEvent(
                    event_type="REPORT_REQUESTED",
                    aggregate_type="request",
                    aggregate_id=uuid.UUID(request_id),
                    payload={"request_id": request_id},
                )
            )
            session.commit()
            return {"status": "NO_IMAGE"}

        # Download input image
        try:
            image_bytes = _download_from_storage(
                settings.storage_bucket_inputs, image_file.storage_path
            )
        except Exception as exc:
            logger.exception("Failed to download image: %s", exc)
            raise self.retry(exc=exc)

        # Apply watermark
        watermark_text = evaluation.watermark_text or f"NeuroHub - {request_id[:8]}"
        try:
            watermarked = apply_watermark(image_bytes, watermark_text)
        except Exception as exc:
            logger.exception("Watermark processing failed: %s", exc)
            raise self.retry(exc=exc)

        # Upload watermarked file
        output_path = (
            f"institutions/{request.institution_id}/requests/{request_id}"
            f"/watermarked/{image_file.file_name or 'output.jpg'}"
        )
        try:
            _upload_to_storage(
                settings.storage_bucket_outputs, output_path, watermarked, "image/jpeg"
            )
        except Exception as exc:
            logger.exception("Failed to upload watermarked file: %s", exc)
            raise self.retry(exc=exc)

        # Update evaluation record
        evaluation.output_storage_path = output_path

        # Emit report generation event
        session.add(
            OutboxEvent(
                event_type="REPORT_REQUESTED",
                aggregate_type="request",
                aggregate_id=uuid.UUID(request_id),
                payload={"request_id": request_id, "watermarked_path": output_path},
            )
        )

        # Notify user
        _create_sync_notification(
            session,
            institution_id=request.institution_id,
            user_id=request.requested_by,
            event_type="WATERMARK_COMPLETED",
            title="워터마크 처리 완료",
            body="워터마크가 적용되었습니다. 보고서 생성이 진행됩니다.",
            entity_type="request",
            entity_id=request.id,
            metadata={"output_path": output_path},
        )

        session.commit()
        logger.info("Watermark completed for request %s", request_id)
        return {"status": "COMPLETED", "output_path": output_path}


def _build_report_content(
    request_id: str,
    service_name: str,
    pipeline_name: str,
    runs: list[dict],
    cases_count: int,
) -> dict:
    """Build structured report content from run results."""
    return {
        "request_id": request_id,
        "service_name": service_name,
        "pipeline_name": pipeline_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases_count": cases_count,
        "summary": {
            "total_runs": len(runs),
            "succeeded": sum(1 for r in runs if r.get("status") == "SUCCEEDED"),
            "failed": sum(1 for r in runs if r.get("status") == "FAILED"),
        },
        "runs": runs,
        "conclusions": [
            {
                "run_id": r["run_id"],
                "result": r.get("result_manifest", {}),
            }
            for r in runs
            if r.get("status") == "SUCCEEDED"
        ],
    }


def _execute_step_container(run, step, session):
    """Execute a single step via Fly Machine container.

    Uses asyncio to call the async ContainerRunner from within the sync Celery task.
    Applies SandboxConfig for resource and security constraints.
    """
    import asyncio

    from app.config import settings as _settings
    from app.services.container_runner import ContainerRunner, app_name_from_job_spec
    from app.services.sandbox_config import SandboxConfig

    job_spec = run.job_spec or {}

    # Build sandbox config from this step's resource requirements
    step_dict = {
        "resources": step.resources if hasattr(step, "resources") and step.resources else {},
        "timeout_seconds": step.timeout_seconds if hasattr(step, "timeout_seconds") else 1800,
    }
    sandbox = SandboxConfig.from_pipeline_step(step_dict)

    # Inject sandbox constraints into job_spec for this execution
    job_spec = dict(job_spec)
    job_spec["sandbox"] = {
        "no_network": sandbox.no_network,
        "memory_mb": sandbox.memory_mb,
        "cpus": sandbox.cpus,
        "timeout_seconds": sandbox.timeout_seconds,
    }

    app_name = app_name_from_job_spec(job_spec)

    runner = ContainerRunner(
        fly_api_token=_settings.fly_api_token,
        fly_org=_settings.fly_org,
        api_base_url=_settings.fly_machines_api_url,
    )

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(
            runner.execute_step(
                app_name=app_name,
                job_spec=job_spec,
                step_index=step.step_index,
                timeout_override=float(sandbox.timeout_seconds),
            )
        )
    finally:
        loop.close()

    step.logs_tail = (result.logs or "")[-2000:]

    if result.status == "SUCCEEDED":
        step.status = "SUCCEEDED"
        step.exit_code = 0
        # Parse and store structured output on the step if it has logs
        if result.logs:
            from app.services.output_parser import parse_container_output
            output_schema = job_spec.get("output_schema")
            parsed = parse_container_output(result.logs, output_schema)
            if hasattr(step, "result_manifest"):
                step.result_manifest = parsed
    elif result.status == "TIMEOUT":
        step.status = "FAILED"
        step.error_detail = result.error or "Container execution timed out"
        raise TimeoutError(step.error_detail)
    else:
        step.status = "FAILED"
        step.error_detail = result.error or f"Container exited with status: {result.status}"
        raise RuntimeError(step.error_detail)


@celery_app.task(
    name="neurohub.tasks.execute_run",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="compute",
)
def execute_run(self, run_id: str):
    """Execute a compute run.

    1. Mark run as RUNNING
    2. Execute each step (simulated with sleep)
    3. Mark run as SUCCEEDED
    4. Record usage in billing ledger
    5. Check if all runs for the request are complete
    6. If yes, transition request COMPUTING -> QC via outbox
    """
    logger.info("Starting execute_run: %s", run_id)

    with sync_session_factory() as session:
        run = session.execute(select(Run).where(Run.id == uuid.UUID(run_id))).scalar_one_or_none()

        if not run:
            logger.error("Run %s not found", run_id)
            return {"run_id": run_id, "status": "NOT_FOUND"}

        if run.status not in ("PENDING", "RUNNING"):
            logger.warning("Run %s in unexpected status %s, skipping", run_id, run.status)
            return {"run_id": run_id, "status": run.status}

        # Mark RUNNING
        run.status = "RUNNING"
        run.celery_task_id = self.request.id
        run.started_at = datetime.now(timezone.utc)
        run.heartbeat_at = datetime.now(timezone.utc)
        session.commit()

    # Execute steps
    try:
        with sync_session_factory() as session:
            from app.models.billing import UsageLedger

            run = session.execute(select(Run).where(Run.id == uuid.UUID(run_id))).scalar_one()

            # Determine execution mode
            from app.config import settings as _settings

            use_containers = _settings.container_execution_enabled and _settings.fly_api_token

            for step in run.steps:
                step.status = "RUNNING"
                step.started_at = datetime.now(timezone.utc)
                session.commit()

                if use_containers and step.docker_image:
                    # Real container execution via Fly Machines
                    _execute_step_container(run, step, session)
                else:
                    # No container configured — log warning but continue
                    logger.warning(
                        "Run %s step %s has no docker_image or container execution disabled; "
                        "marking step as succeeded without execution",
                        run_id,
                        getattr(step, "step_index", "?"),
                    )

                step.status = "SUCCEEDED"
                step.completed_at = datetime.now(timezone.utc)
                step.exit_code = 0
                run.heartbeat_at = datetime.now(timezone.utc)
                session.commit()

            # Collect and parse output from the final step's logs
            from app.services.output_parser import extract_qc_metrics, parse_container_output

            last_step_logs = ""
            if run.steps:
                last_step = run.steps[-1]
                last_step_logs = getattr(last_step, "logs_tail", "") or ""

            output_schema = (run.job_spec or {}).get("output_schema")
            result_manifest = parse_container_output(last_step_logs, output_schema)
            qc_data = extract_qc_metrics(result_manifest)

            # Mark run SUCCEEDED
            run.status = "SUCCEEDED"
            run.completed_at = datetime.now(timezone.utc)
            run.result_manifest = {
                **result_manifest,
                "steps_completed": len(run.steps),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            if hasattr(run, "metrics"):
                run.metrics = qc_data

            # Record usage capture in billing ledger
            service_id = run.job_spec.get("service_id") if run.job_spec else None
            service_version = (
                run.job_spec.get("service_version", "1.0.0") if run.job_spec else "1.0.0"
            )
            if service_id:
                session.add(
                    UsageLedger(
                        institution_id=run.institution_id,
                        request_id=run.request_id,
                        run_id=run.id,
                        service_id=uuid.UUID(service_id)
                        if isinstance(service_id, str)
                        else service_id,
                        service_version=service_version,
                        charge_type="CAPTURE",
                        units=1,
                        unit_price=0,
                        amount=0,
                        currency="KRW",
                    )
                )

            session.commit()

            # Check if ALL runs for this request are complete
            request_id = run.request_id
            all_runs = (
                session.execute(select(Run).where(Run.request_id == request_id)).scalars().all()
            )

            all_succeeded = all(r.status == "SUCCEEDED" for r in all_runs)
            any_failed = any(r.status == "FAILED" for r in all_runs)

            if all_succeeded:
                # Transition request COMPUTING -> QC via outbox
                request = session.execute(
                    select(Request).where(Request.id == request_id)
                ).scalar_one()

                if request.status == "COMPUTING":
                    request.status = "QC"
                    session.add(
                        OutboxEvent(
                            event_type="COMPUTING_COMPLETE",
                            aggregate_type="request",
                            aggregate_id=request_id,
                            payload={"request_id": str(request_id)},
                        )
                    )
                    _create_sync_notification(
                        session,
                        institution_id=request.institution_id,
                        user_id=request.requested_by,
                        event_type="COMPUTING_COMPLETE",
                        title="AI 분석 완료",
                        body="모든 분석이 완료되었습니다. 품질 검증 단계로 이동합니다.",
                        entity_type="request",
                        entity_id=request.id,
                        metadata={"status": "QC"},
                    )

                    # Notify evaluators assigned to this service
                    _notify_service_evaluators(
                        session,
                        service_id=request.service_id,
                        institution_id=request.institution_id,
                        event_type="QC_REVIEW_REQUESTED",
                        title="평가 요청",
                        body="새로운 분석 결과가 전문가 평가를 기다리고 있습니다.",
                        entity_type="request",
                        entity_id=request.id,
                    )

                    session.commit()
                    logger.info("All runs succeeded for request %s, moved to QC", request_id)

            elif any_failed and not any(r.status in ("PENDING", "RUNNING") for r in all_runs):
                request = session.execute(
                    select(Request).where(Request.id == request_id)
                ).scalar_one()
                if request.status == "COMPUTING":
                    request.status = "FAILED"
                    request.error_detail = "One or more runs failed"
                    _create_sync_notification(
                        session,
                        institution_id=request.institution_id,
                        user_id=request.requested_by,
                        event_type="COMPUTING_FAILED",
                        title="분석 실패",
                        body="하나 이상의 분석 작업이 실패했습니다.",
                        entity_type="request",
                        entity_id=request.id,
                        metadata={"status": "FAILED"},
                    )
                    session.commit()

        logger.info("Run %s completed successfully", run_id)
        return {"run_id": run_id, "status": "SUCCEEDED"}

    except Exception as exc:
        logger.exception("Run %s failed: %s", run_id, exc)

        with sync_session_factory() as session:
            from app.models.billing import UsageLedger

            run = session.execute(
                select(Run).where(Run.id == uuid.UUID(run_id))
            ).scalar_one_or_none()
            if run and run.status == "RUNNING":
                run.status = "FAILED"
                run.error_detail = str(exc)[:2000]
                run.completed_at = datetime.now(timezone.utc)

                # Record usage release on failure
                service_id = run.job_spec.get("service_id") if run.job_spec else None
                service_version = (
                    run.job_spec.get("service_version", "1.0.0") if run.job_spec else "1.0.0"
                )
                if service_id:
                    session.add(
                        UsageLedger(
                            institution_id=run.institution_id,
                            request_id=run.request_id,
                            run_id=run.id,
                            service_id=uuid.UUID(service_id)
                            if isinstance(service_id, str)
                            else service_id,
                            service_version=service_version,
                            charge_type="RELEASE",
                            units=1,
                            unit_price=0,
                            amount=0,
                            currency="KRW",
                        )
                    )

                session.commit()

        raise self.retry(exc=exc)


@celery_app.task(
    name="neurohub.tasks.generate_report",
    bind=True,
    max_retries=2,
    default_retry_delay=15,
    queue="reporting",
)
def generate_report(self, request_id: str):
    """Generate a report for a completed request.

    1. Load request and all runs (succeeded and failed)
    2. Build structured report content via _build_report_content
    3. Create a Report record with COMPLETED status
    4. Transition request to REPORTING -> FINAL (or EXPERT_REVIEW)
    5. Emit outbox event for downstream consumers
    """
    logger.info("Starting generate_report for request: %s", request_id)

    with sync_session_factory() as session:
        from app.models.service import PipelineDefinition, ServiceDefinition

        request = session.execute(
            select(Request).where(Request.id == uuid.UUID(request_id))
        ).scalar_one_or_none()

        if not request:
            logger.error("Request %s not found", request_id)
            return {"request_id": request_id, "status": "NOT_FOUND"}

        # Get all runs (not just succeeded) for comprehensive reporting
        runs = (
            session.execute(select(Run).where(Run.request_id == uuid.UUID(request_id)))
            .scalars()
            .all()
        )

        # Get service/pipeline info for report metadata
        service = session.execute(
            select(ServiceDefinition).where(ServiceDefinition.id == request.service_id)
        ).scalar_one_or_none()

        pipeline = session.execute(
            select(PipelineDefinition).where(PipelineDefinition.id == request.pipeline_id)
        ).scalar_one_or_none()

        runs_data = [
            {
                "run_id": str(r.id),
                "case_id": str(r.case_id),
                "status": r.status,
                "result_manifest": r.result_manifest or {},
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ]

        # Use service/pipeline snapshot from request if live lookup fails
        service_name = (
            service.display_name
            if service
            else (request.service_snapshot or {}).get("display_name", "N/A")
        )
        pipeline_name = (
            pipeline.name if pipeline else (request.pipeline_snapshot or {}).get("name", "N/A")
        )

        # Build structured report content
        content = _build_report_content(
            request_id=str(request.id),
            service_name=service_name,
            pipeline_name=pipeline_name,
            runs=runs_data,
            cases_count=len(request.cases) if request.cases else 0,
        )

        # Look up watermarked path from evaluation
        from app.models.evaluation import Evaluation

        watermarked_path = None
        eval_result = session.execute(
            select(Evaluation)
            .where(Evaluation.request_id == uuid.UUID(request_id))
            .order_by(Evaluation.created_at.desc())
            .limit(1)
        )
        evaluation = eval_result.scalar_one_or_none()
        if evaluation and evaluation.output_storage_path:
            watermarked_path = evaluation.output_storage_path

        report = Report(
            institution_id=request.institution_id,
            request_id=request.id,
            status="COMPLETED",
            title=f"분석 보고서 - {service_name}",
            content=content,
            summary=f"총 {len(runs)}건의 분석 중 {content['summary']['succeeded']}건 성공, "
            f"{content['summary']['failed']}건 실패.",
            watermarked_storage_path=watermarked_path,
            generated_at=datetime.now(timezone.utc),
            celery_task_id=self.request.id,
        )
        session.add(report)

        # Transition: determine if expert review is needed
        pipeline_snapshot = request.pipeline_snapshot or {}
        needs_expert_review = pipeline_snapshot.get("qc_rules", {}).get(
            "require_expert_review", False
        )
        any_failed = any(r.status == "FAILED" for r in runs)

        if request.status == "REPORTING":
            if needs_expert_review or any_failed:
                request.status = "EXPERT_REVIEW"
                event_type = "EXPERT_REVIEW_NEEDED"
            else:
                request.status = "FINAL"
                event_type = "REPORT_GENERATED"
        elif request.status == "QC":
            # If called after QC pass, move to REPORTING first
            request.status = "REPORTING"
            event_type = "REPORT_GENERATED"
        else:
            event_type = "REPORT_GENERATED"

        session.add(
            OutboxEvent(
                event_type=event_type,
                aggregate_type="request",
                aggregate_id=request.id,
                payload={
                    "request_id": request_id,
                    "report_id": str(report.id) if report.id else None,
                    "status": request.status,
                },
            )
        )

        # Notify the request owner
        if request.status == "FINAL":
            _create_sync_notification(
                session,
                institution_id=request.institution_id,
                user_id=request.requested_by,
                event_type="REPORT_GENERATED",
                title="보고서 생성 완료",
                body="분석 보고서가 생성되었습니다. 결과를 확인하세요.",
                entity_type="request",
                entity_id=request.id,
                metadata={"status": "FINAL", "report_id": str(report.id) if report.id else None},
            )
        elif request.status == "EXPERT_REVIEW":
            _create_sync_notification(
                session,
                institution_id=request.institution_id,
                user_id=request.requested_by,
                event_type="EXPERT_REVIEW_NEEDED",
                title="전문가 검토 대기",
                body="보고서가 전문가 검토 단계로 이동했습니다.",
                entity_type="request",
                entity_id=request.id,
                metadata={"status": "EXPERT_REVIEW"},
            )

            # Notify evaluators assigned to this service
            _notify_service_evaluators(
                session,
                service_id=request.service_id,
                institution_id=request.institution_id,
                event_type="EXPERT_REVIEW_NEEDED",
                title="전문가 검토 요청",
                body="보고서가 전문가 검토 단계에 있습니다. 평가를 진행해주세요.",
                entity_type="request",
                entity_id=request.id,
            )

        session.commit()

        # Trigger PDF generation as a follow-up task
        celery_app.send_task(
            "neurohub.tasks.generate_pdf_report",
            args=[request_id],
            queue="reporting",
        )
        logger.info("Triggered generate_pdf_report for request %s", request_id)

        logger.info("Report generated for request %s (status: %s)", request_id, request.status)
        return {"request_id": request_id, "status": "COMPLETED"}


# ── Technique Run Execution Task ─────────────────────────────────────────


@celery_app.task(
    name="neurohub.tasks.execute_technique_run",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="compute",
)
def execute_technique_run(self, technique_run_id: str):
    """Execute a single technique run via LocalContainerRunner.

    1. Load TechniqueRun from DB
    2. Resolve input/output paths from the parent run's case data
    3. Execute container via LocalContainerRunner
    4. Parse NEUROHUB_OUTPUT and update TechniqueRun
    5. Check if all sibling technique runs are done
    6. If yes, run fusion and update parent Run
    """
    import asyncio

    from app.config import settings as _settings
    from app.models.technique import TechniqueRun

    logger.info("Starting execute_technique_run: %s", technique_run_id)

    if not _settings.local_docker_enabled:
        logger.warning(
            "local_docker_enabled=false, skipping technique run %s", technique_run_id
        )
        return {"technique_run_id": technique_run_id, "status": "SKIPPED"}

    with sync_session_factory() as session:
        tr = session.execute(
            select(TechniqueRun).where(TechniqueRun.id == uuid.UUID(technique_run_id))
        ).scalar_one_or_none()

        if not tr:
            logger.error("TechniqueRun %s not found", technique_run_id)
            return {"technique_run_id": technique_run_id, "status": "NOT_FOUND"}

        if tr.status not in ("PENDING", "RUNNING"):
            logger.warning(
                "TechniqueRun %s in status %s, skipping", technique_run_id, tr.status
            )
            return {"technique_run_id": technique_run_id, "status": tr.status}

        # Mark as RUNNING
        tr.status = "RUNNING"
        tr.started_at = datetime.now(timezone.utc)
        tr.celery_task_id = self.request.id
        session.commit()

        # Get parent run for input/output path resolution
        run = session.execute(
            select(Run).where(Run.id == tr.run_id)
        ).scalar_one_or_none()

        if not run:
            logger.error("Parent run not found for TechniqueRun %s", technique_run_id)
            tr.status = "FAILED"
            tr.error_detail = "Parent run not found"
            session.commit()
            return {"technique_run_id": technique_run_id, "status": "FAILED"}

        job_spec = tr.job_spec or {}
        docker_image = job_spec.get("docker_image", "")
        technique_key = tr.technique_key

        # Resolve input directory from run's case data
        # Convention: /data/inputs/{institution_id}/{request_id}/{case_id}/bids/
        input_dir = _resolve_technique_input_dir(run, session)
        output_dir = f"/tmp/neurohub/technique_outputs/{technique_run_id}"

    # Execute container
    try:
        from app.services.local_container_runner import LocalContainerRunner

        runner = LocalContainerRunner()

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                runner.execute_technique(
                    technique_key=technique_key,
                    docker_image=docker_image,
                    input_dir=input_dir,
                    output_dir=output_dir,
                    job_spec=job_spec,
                    timeout=job_spec.get("timeout", 7200),
                    gpu=job_spec.get("resource_requirements", {}).get("gpu", False),
                )
            )
        finally:
            loop.close()

        with sync_session_factory() as session:
            tr = session.execute(
                select(TechniqueRun).where(
                    TechniqueRun.id == uuid.UUID(technique_run_id)
                )
            ).scalar_one()

            if result.exit_code == 0 and result.technique_output:
                tr.status = "COMPLETED"
                tr.output_data = result.technique_output
                tr.qc_score = result.technique_output.get("qc_score")
                tr.completed_at = datetime.now(timezone.utc)
                logger.info(
                    "TechniqueRun %s completed: qc=%.1f, features=%d",
                    technique_run_id,
                    tr.qc_score or 0,
                    len(result.technique_output.get("features", {})),
                )
            else:
                tr.status = "FAILED"
                tr.error_detail = (
                    f"Container exit={result.exit_code}, "
                    f"output={'found' if result.technique_output else 'missing'}\n"
                    f"{result.logs[-500:]}"
                )
                tr.completed_at = datetime.now(timezone.utc)
                logger.error(
                    "TechniqueRun %s failed: exit=%d",
                    technique_run_id, result.exit_code,
                )

            session.commit()

            # Check if all sibling technique runs are done
            siblings = (
                session.execute(
                    select(TechniqueRun).where(TechniqueRun.run_id == tr.run_id)
                )
                .scalars()
                .all()
            )

            all_done = all(s.status in ("COMPLETED", "FAILED") for s in siblings)
            if all_done:
                _finalize_technique_runs(session, tr.run_id, siblings)

        return {"technique_run_id": technique_run_id, "status": tr.status}

    except Exception as exc:
        logger.exception("TechniqueRun %s execution error: %s", technique_run_id, exc)
        with sync_session_factory() as session:
            tr = session.execute(
                select(TechniqueRun).where(
                    TechniqueRun.id == uuid.UUID(technique_run_id)
                )
            ).scalar_one_or_none()
            if tr and tr.status == "RUNNING":
                tr.status = "FAILED"
                tr.error_detail = str(exc)[:2000]
                tr.completed_at = datetime.now(timezone.utc)
                tr.retry_count = (tr.retry_count or 0) + 1
                session.commit()
        raise self.retry(exc=exc)


def _resolve_technique_input_dir(run: Run, session) -> str:
    """Resolve the BIDS input directory for a technique run.

    Checks run.job_spec for input_dir override, otherwise builds path from
    institution/request/case structure.
    """
    job_spec = run.job_spec or {}

    # Direct override from job_spec
    if job_spec.get("input_dir"):
        return job_spec["input_dir"]

    # Build from case files
    from app.models.request import Request

    request = session.execute(
        select(Request).where(Request.id == run.request_id)
    ).scalar_one_or_none()

    if request:
        # Convention: data stored in /data/inputs/{inst}/{req}/bids/
        return (
            f"/data/inputs/{request.institution_id}/{request.id}/bids"
        )

    return f"/tmp/neurohub/inputs/{run.id}"


def _finalize_technique_runs(session, run_id: uuid.UUID, technique_runs: list) -> None:
    """After all technique runs complete, run fusion and update parent Run."""
    from app.services.fusion_engine import FusionConfig, run_fusion
    from app.services.technique_output import validate_technique_output

    run = session.execute(
        select(Run).where(Run.id == run_id)
    ).scalar_one_or_none()
    if not run:
        return

    # Collect completed outputs
    outputs = []
    for tr in technique_runs:
        if tr.status == "COMPLETED" and tr.output_data:
            try:
                out = validate_technique_output(tr.output_data, tr.technique_key)
                outputs.append(out)
            except ValueError as e:
                logger.warning("Invalid output for technique run %s: %s", tr.id, e)

    completed_count = sum(1 for tr in technique_runs if tr.status == "COMPLETED")
    failed_count = sum(1 for tr in technique_runs if tr.status == "FAILED")

    if not outputs:
        # All failed
        run.status = "FAILED"
        run.error_detail = f"All {failed_count} technique runs failed"
        run.completed_at = datetime.now(timezone.utc)
        logger.error("All technique runs failed for run %s", run_id)
    else:
        # Run fusion
        try:
            # Build weights from technique run job specs
            technique_weights = {}
            for tr in technique_runs:
                if tr.job_spec and tr.status == "COMPLETED":
                    technique_weights[tr.technique_key] = tr.job_spec.get(
                        "base_weight", 1.0 / len(technique_runs)
                    )

            config = FusionConfig(
                service_id=str(run.job_spec.get("service_id", "")) if run.job_spec else "",
                technique_weights=technique_weights,
            )

            fusion_result = run_fusion(outputs, config)

            run.status = "SUCCEEDED"
            run.completed_at = datetime.now(timezone.utc)
            run.result_manifest = {
                "fusion": fusion_result.to_dict(),
                "techniques_completed": completed_count,
                "techniques_failed": failed_count,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            logger.info(
                "Fusion complete for run %s: %d included, confidence=%.1f",
                run_id,
                len(fusion_result.included_modules),
                fusion_result.confidence_score,
            )
        except Exception as e:
            logger.exception("Fusion failed for run %s: %s", run_id, e)
            run.status = "SUCCEEDED"  # Still mark succeeded — techniques ran
            run.completed_at = datetime.now(timezone.utc)
            run.result_manifest = {
                "fusion_error": str(e),
                "techniques_completed": completed_count,
                "techniques_failed": failed_count,
            }

    # Transition parent request if applicable
    request = session.execute(
        select(Request).where(Request.id == run.request_id)
    ).scalar_one_or_none()

    if request and request.status == "COMPUTING":
        all_runs = (
            session.execute(select(Run).where(Run.request_id == request.id))
            .scalars()
            .all()
        )
        if all(r.status in ("SUCCEEDED", "FAILED") for r in all_runs):
            any_succeeded = any(r.status == "SUCCEEDED" for r in all_runs)
            if any_succeeded:
                request.status = "QC"
                _create_sync_notification(
                    session,
                    institution_id=request.institution_id,
                    user_id=request.requested_by,
                    event_type="COMPUTING_COMPLETE",
                    title="AI 분석 완료",
                    body="모든 기법 분석이 완료되었습니다. 품질 검증 단계로 이동합니다.",
                    entity_type="request",
                    entity_id=request.id,
                )
            else:
                request.status = "FAILED"
                request.error_detail = "All runs failed"

    session.commit()


# ── Process Case Upload Task ─────────────────────────────────────────────


@celery_app.task(
    name="neurohub.tasks.process_case_upload",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    queue="compute",
)
def process_case_upload(
    self,
    request_id: str,
    case_id: str,
    zip_storage_path: str,
):
    """Process an uploaded zip file through the full analysis pipeline.

    1. Download zip from storage to local temp dir
    2. Extract + smart-scan for DICOM/NIfTI files
    3. Run BIDS conversion, Pre-QC, technique execution, fusion
    4. Update Run/Request status in DB
    5. Trigger report generation if all cases complete

    This task is the main entry point for the automated pipeline.
    It bridges the gap between file upload and analysis results.
    """
    import os
    import tempfile

    logger.info(
        "Starting process_case_upload: request=%s case=%s zip=%s",
        request_id, case_id, zip_storage_path,
    )

    with sync_session_factory() as session:
        request = session.execute(
            select(Request).where(Request.id == uuid.UUID(request_id))
        ).scalar_one_or_none()

        if not request:
            logger.error("Request %s not found", request_id)
            return {"status": "NOT_FOUND"}

        from app.models.request import Case
        case = session.execute(
            select(Case).where(Case.id == uuid.UUID(case_id))
        ).scalar_one_or_none()

        if not case:
            logger.error("Case %s not found", case_id)
            return {"status": "NOT_FOUND"}

        service_id = str(request.service_id) if request.service_id else None
        patient_ref = case.patient_ref or "unknown"

    # Create working directory
    work_dir = tempfile.mkdtemp(prefix=f"neurohub_pipeline_{case_id[:8]}_")

    try:
        # Download zip from storage
        zip_path = os.path.join(work_dir, "upload.zip")
        _download_from_storage(zip_storage_path, zip_path)

        # Run the full pipeline
        from app.services.pipeline_orchestrator import PipelineOrchestrator

        orchestrator = PipelineOrchestrator(
            work_dir=work_dir,
            request_id=request_id,
            case_id=case_id,
            service_id=service_id,
            patient_ref=patient_ref,
        )
        result = orchestrator.run_full_pipeline(zip_path)

        # Update DB with results
        with sync_session_factory() as session:
            # Update or create Run
            run = session.execute(
                select(Run).where(
                    Run.request_id == uuid.UUID(request_id),
                    Run.case_id == uuid.UUID(case_id),
                )
            ).scalar_one_or_none()

            if not run:
                # Create a new Run for this case
                inst_id = session.execute(
                    select(Request.institution_id).where(
                        Request.id == uuid.UUID(request_id)
                    )
                ).scalar_one()

                run = Run(
                    institution_id=inst_id,
                    request_id=uuid.UUID(request_id),
                    case_id=uuid.UUID(case_id),
                    status="RUNNING",
                    started_at=datetime.now(timezone.utc),
                    celery_task_id=self.request.id,
                    job_spec={
                        "pipeline": "auto_process",
                        "service_id": service_id,
                        "zip_path": zip_storage_path,
                    },
                )
                session.add(run)
                session.flush()

            if result.status in ("COMPLETED", "PARTIAL"):
                run.status = "SUCCEEDED"
                run.completed_at = datetime.now(timezone.utc)
                run.result_manifest = result.to_dict()
                if result.status == "PARTIAL":
                    run.error_detail = "Pre-QC blocked technique execution"
            else:
                run.status = "FAILED"
                run.completed_at = datetime.now(timezone.utc)
                run.error_detail = "; ".join(result.errors[:3])
                run.result_manifest = result.to_dict()

            # Check if all runs for this request are done → advance status
            request = session.execute(
                select(Request).where(Request.id == uuid.UUID(request_id))
            ).scalar_one()

            if request.status == "COMPUTING":
                all_runs = (
                    session.execute(
                        select(Run).where(Run.request_id == uuid.UUID(request_id))
                    )
                    .scalars()
                    .all()
                )
                if all(r.status in ("SUCCEEDED", "FAILED") for r in all_runs):
                    any_succeeded = any(r.status == "SUCCEEDED" for r in all_runs)
                    if any_succeeded:
                        request.status = "QC"
                        _create_sync_notification(
                            session,
                            institution_id=request.institution_id,
                            user_id=request.requested_by,
                            event_type="COMPUTING_COMPLETE",
                            title="AI 분석 완료",
                            body="자동 분석 파이프라인이 완료되었습니다. 품질 검증을 확인해 주세요.",
                            entity_type="request",
                            entity_id=request.id,
                        )
                    else:
                        request.status = "FAILED"
                        request.error_detail = "All pipeline runs failed"

            session.commit()

        return {
            "status": result.status,
            "request_id": request_id,
            "case_id": case_id,
            "stages": len(result.stages),
            "modalities": result.modalities_found,
            "can_proceed": result.can_proceed,
            "technique_runs": len(result.technique_runs),
        }

    except Exception as exc:
        logger.exception("Pipeline failed for case %s: %s", case_id, exc)

        with sync_session_factory() as session:
            request = session.execute(
                select(Request).where(Request.id == uuid.UUID(request_id))
            ).scalar_one_or_none()

            if request and request.status == "COMPUTING":
                request.status = "FAILED"
                request.error_detail = f"Pipeline error: {str(exc)[:500]}"

            if request:
                _create_sync_notification(
                    session,
                    institution_id=request.institution_id,
                    user_id=request.requested_by,
                    event_type="PIPELINE_FAILED",
                    title="분석 파이프라인 오류",
                    body=f"분석 처리 중 오류가 발생했습니다: {str(exc)[:200]}",
                    entity_type="request",
                    entity_id=uuid.UUID(request_id),
                )
            session.commit()

        raise self.retry(exc=exc)

    finally:
        # Clean up work directory
        import shutil as _shutil
        if os.path.exists(work_dir):
            try:
                _shutil.rmtree(work_dir)
            except Exception:
                logger.warning("Failed to clean up work dir: %s", work_dir)


def _download_from_storage(storage_path: str, local_path: str) -> None:
    """Download a file from MinIO/Supabase storage to local disk."""
    import asyncio as _asyncio

    from app.config import settings as _settings

    async def _download():
        from app.services.storage import download_file
        await download_file(
            bucket=_settings.storage_bucket_inputs,
            path=storage_path,
            local_path=local_path,
        )

    try:
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(_asyncio.run, _download()).result()
        else:
            loop.run_until_complete(_download())
    except RuntimeError:
        _asyncio.run(_download())
