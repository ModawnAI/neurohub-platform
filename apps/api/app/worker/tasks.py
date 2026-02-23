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
from app.models.run import Run, RunStep
from app.worker.celery_app import celery_app


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
    session.add(Notification(
        institution_id=institution_id,
        user_id=user_id,
        event_type=event_type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_=metadata or {},
    ))

logger = logging.getLogger("neurohub.worker")


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
    import hashlib
    import hmac
    import json

    import httpx

    from app.models.webhook import Webhook, WebhookDeliveryLog
    from app.services.webhook_service import build_webhook_payload, generate_webhook_signature

    logger.info("Delivering webhook %s event=%s (attempt %d)", webhook_id, event_type, self.request.retries + 1)

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
        session.add(WebhookDeliveryLog(
            webhook_id=webhook.id,
            event_type=event_type,
            payload=payload,
            status_code=status_code,
            response_body=response_body,
            success=success,
            attempt=self.request.retries + 1,
            error_detail=error_detail,
        ))

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
                logger.warning("Webhook %s paused after %d failures", webhook_id, webhook.failure_count)
            session.commit()

            # Exponential backoff: 10s, 20s, 40s, 80s, 160s
            raise self.retry(
                countdown=10 * (2 ** self.request.retries),
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
            select(Report).where(Report.request_id == uuid.UUID(request_id))
            .order_by(Report.created_at.desc()).limit(1)
        ).scalar_one_or_none()

        if not report:
            logger.error("No report record found for request %s", request_id)
            return {"request_id": request_id, "status": "NO_REPORT"}

        # Gather data for PDF
        runs = session.execute(
            select(Run).where(Run.request_id == uuid.UUID(request_id))
        ).scalars().all()

        qc_decisions = session.execute(
            select(QCDecision).where(QCDecision.request_id == uuid.UUID(request_id))
            .order_by(QCDecision.created_at.desc())
        ).scalars().all()

        from app.models.report import ReportReview
        reviews = session.execute(
            select(ReportReview).where(ReportReview.report_id == report.id)
            .order_by(ReportReview.created_at.desc())
        ).scalars().all()

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
        run = session.execute(
            select(Run).where(Run.id == uuid.UUID(run_id))
        ).scalar_one_or_none()

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

            run = session.execute(
                select(Run).where(Run.id == uuid.UUID(run_id))
            ).scalar_one()

            for step in run.steps:
                step.status = "RUNNING"
                step.started_at = datetime.now(timezone.utc)
                session.commit()

                # Simulated work (1 second per step)
                time.sleep(1)

                step.status = "SUCCEEDED"
                step.completed_at = datetime.now(timezone.utc)
                step.exit_code = 0
                run.heartbeat_at = datetime.now(timezone.utc)
                session.commit()

            # Mark run SUCCEEDED
            run.status = "SUCCEEDED"
            run.completed_at = datetime.now(timezone.utc)
            run.result_manifest = {
                "status": "completed",
                "steps_completed": len(run.steps),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

            # Record usage capture in billing ledger
            service_id = run.job_spec.get("service_id") if run.job_spec else None
            service_version = run.job_spec.get("service_version", "1.0.0") if run.job_spec else "1.0.0"
            if service_id:
                session.add(UsageLedger(
                    institution_id=run.institution_id,
                    request_id=run.request_id,
                    run_id=run.id,
                    service_id=uuid.UUID(service_id) if isinstance(service_id, str) else service_id,
                    service_version=service_version,
                    charge_type="CAPTURE",
                    units=1,
                    unit_price=0,
                    amount=0,
                    currency="KRW",
                ))

            session.commit()

            # Check if ALL runs for this request are complete
            request_id = run.request_id
            all_runs = session.execute(
                select(Run).where(Run.request_id == request_id)
            ).scalars().all()

            all_succeeded = all(r.status == "SUCCEEDED" for r in all_runs)
            any_failed = any(r.status == "FAILED" for r in all_runs)

            if all_succeeded:
                # Transition request COMPUTING -> QC via outbox
                request = session.execute(
                    select(Request).where(Request.id == request_id)
                ).scalar_one()

                if request.status == "COMPUTING":
                    request.status = "QC"
                    session.add(OutboxEvent(
                        event_type="COMPUTING_COMPLETE",
                        aggregate_type="request",
                        aggregate_id=request_id,
                        payload={"request_id": str(request_id)},
                    ))
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
                service_version = run.job_spec.get("service_version", "1.0.0") if run.job_spec else "1.0.0"
                if service_id:
                    session.add(UsageLedger(
                        institution_id=run.institution_id,
                        request_id=run.request_id,
                        run_id=run.id,
                        service_id=uuid.UUID(service_id) if isinstance(service_id, str) else service_id,
                        service_version=service_version,
                        charge_type="RELEASE",
                        units=1,
                        unit_price=0,
                        amount=0,
                        currency="KRW",
                    ))

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
        from app.models.service import ServiceDefinition, PipelineDefinition

        request = session.execute(
            select(Request).where(Request.id == uuid.UUID(request_id))
        ).scalar_one_or_none()

        if not request:
            logger.error("Request %s not found", request_id)
            return {"request_id": request_id, "status": "NOT_FOUND"}

        # Get all runs (not just succeeded) for comprehensive reporting
        runs = session.execute(
            select(Run).where(Run.request_id == uuid.UUID(request_id))
        ).scalars().all()

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
            service.display_name if service
            else (request.service_snapshot or {}).get("display_name", "N/A")
        )
        pipeline_name = (
            pipeline.name if pipeline
            else (request.pipeline_snapshot or {}).get("name", "N/A")
        )

        # Build structured report content
        content = _build_report_content(
            request_id=str(request.id),
            service_name=service_name,
            pipeline_name=pipeline_name,
            runs=runs_data,
            cases_count=len(request.cases) if request.cases else 0,
        )

        report = Report(
            institution_id=request.institution_id,
            request_id=request.id,
            status="COMPLETED",
            title=f"분석 보고서 - {service_name}",
            content=content,
            summary=f"총 {len(runs)}건의 분석 중 {content['summary']['succeeded']}건 성공, "
                    f"{content['summary']['failed']}건 실패.",
            generated_at=datetime.now(timezone.utc),
            celery_task_id=self.request.id,
        )
        session.add(report)

        # Transition: determine if expert review is needed
        pipeline_snapshot = request.pipeline_snapshot or {}
        needs_expert_review = pipeline_snapshot.get("qc_rules", {}).get("require_expert_review", False)
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

        session.add(OutboxEvent(
            event_type=event_type,
            aggregate_type="request",
            aggregate_id=request.id,
            payload={
                "request_id": request_id,
                "report_id": str(report.id) if report.id else None,
                "status": request.status,
            },
        ))

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

        session.commit()

        logger.info("Report generated for request %s (status: %s)", request_id, request.status)
        return {"request_id": request_id, "status": "COMPLETED"}
