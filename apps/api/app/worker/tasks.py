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


@celery_app.task(name="neurohub.tasks.execute_run", bind=True, max_retries=3, default_retry_delay=30)
def execute_run(self, run_id: str):
    """Execute a compute run.

    1. Mark run as RUNNING
    2. Execute each step (simulated with sleep)
    3. Mark run as SUCCEEDED
    4. Check if all runs for the request are complete
    5. If yes, transition request COMPUTING → QC via outbox
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
            session.commit()

            # Check if ALL runs for this request are complete
            request_id = run.request_id
            all_runs = session.execute(
                select(Run).where(Run.request_id == request_id)
            ).scalars().all()

            all_succeeded = all(r.status == "SUCCEEDED" for r in all_runs)
            any_failed = any(r.status == "FAILED" for r in all_runs)

            if all_succeeded:
                # Transition request COMPUTING → QC via outbox
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
            run = session.execute(
                select(Run).where(Run.id == uuid.UUID(run_id))
            ).scalar_one_or_none()
            if run and run.status == "RUNNING":
                run.status = "FAILED"
                run.error_detail = str(exc)[:2000]
                run.completed_at = datetime.now(timezone.utc)
                session.commit()

        raise self.retry(exc=exc)


@celery_app.task(name="neurohub.tasks.generate_report", bind=True, max_retries=2, default_retry_delay=15)
def generate_report(self, request_id: str):
    """Generate a report for a completed request.

    1. Load request and all succeeded runs
    2. Create a Report record
    3. Aggregate results into report content
    4. Transition request to REPORTING → FINAL (or EXPERT_REVIEW)
    """
    logger.info("Starting generate_report for request: %s", request_id)

    with sync_session_factory() as session:
        request = session.execute(
            select(Request).where(Request.id == uuid.UUID(request_id))
        ).scalar_one_or_none()

        if not request:
            logger.error("Request %s not found", request_id)
            return {"request_id": request_id, "status": "NOT_FOUND"}

        runs = session.execute(
            select(Run).where(
                Run.request_id == uuid.UUID(request_id),
                Run.status == "SUCCEEDED",
            )
        ).scalars().all()

        # Build report content from run results
        content = {
            "request_id": request_id,
            "service": request.service_snapshot or {},
            "case_results": [],
        }
        for run in runs:
            content["case_results"].append({
                "run_id": str(run.id),
                "case_id": str(run.case_id),
                "result_manifest": run.result_manifest or {},
            })

        report = Report(
            institution_id=request.institution_id,
            request_id=request.id,
            status="COMPLETED",
            title=f"분석 보고서 - {(request.service_snapshot or {}).get('display_name', 'N/A')}",
            content=content,
            summary=f"총 {len(runs)}건의 분석이 완료되었습니다.",
            generated_at=datetime.now(timezone.utc),
        )
        session.add(report)

        # Transition: determine if expert review is needed
        pipeline = request.pipeline_snapshot or {}
        needs_expert_review = pipeline.get("qc_rules", {}).get("require_expert_review", False)

        if request.status == "REPORTING":
            if needs_expert_review:
                request.status = "EXPERT_REVIEW"
            else:
                request.status = "FINAL"
        elif request.status == "QC":
            # If called after QC pass, move to REPORTING first
            request.status = "REPORTING"

        session.add(OutboxEvent(
            event_type="REPORT_GENERATED",
            aggregate_type="request",
            aggregate_id=request.id,
            payload={
                "request_id": request_id,
                "report_id": str(report.id) if report.id else None,
            },
        ))
        session.commit()

        logger.info("Report generated for request %s", request_id)
        return {"request_id": request_id, "status": "COMPLETED"}
