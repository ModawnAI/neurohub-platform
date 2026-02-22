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
from app.models.outbox import OutboxEvent
from app.models.report import Report
from app.models.request import Request
from app.models.run import Run, RunStep
from app.worker.celery_app import celery_app

logger = logging.getLogger("neurohub.worker")


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
                    session.commit()
                    logger.info("All runs succeeded for request %s, moved to QC", request_id)

            elif any_failed and not any(r.status in ("PENDING", "RUNNING") for r in all_runs):
                request = session.execute(
                    select(Request).where(Request.id == request_id)
                ).scalar_one()
                if request.status == "COMPUTING":
                    request.status = "FAILED"
                    request.error_detail = "One or more runs failed"
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
        session.commit()

        logger.info("Report generated for request %s (status: %s)", request_id, request.status)
        return {"request_id": request_id, "status": "COMPLETED"}
