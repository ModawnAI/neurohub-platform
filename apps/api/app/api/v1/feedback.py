"""Feedback collection and training job management endpoints."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from app.dependencies import AuthenticatedUser, DbSession, require_roles
from app.models.feedback import ModelFeedback, ModelPerformanceMetrics, ModelTrainingJob
from app.models.run import Run
from app.models.service import ServiceDefinition
from app.schemas.feedback import (
    FeedbackCreate, FeedbackRead, FeedbackStats,
    PerformanceTimeSeries, PerformanceMetricsRead, TrainingJobCreate, TrainingJobRead,
)

router = APIRouter(tags=["Feedback & Learning"])
logger = logging.getLogger("neurohub.feedback")

FEEDBACK_THRESHOLD = 50  # auto-trigger training after this many high-quality feedbacks


# ── Feedback endpoints ────────────────────────────────────────────────────


@router.post("/evaluations/{evaluation_id}/feedback", response_model=FeedbackRead, status_code=201)
async def submit_feedback(
    evaluation_id: uuid.UUID,
    body: FeedbackCreate,
    db: DbSession,
    user: Annotated[AuthenticatedUser, Depends(require_roles("EXPERT", "ADMIN"))],
):
    """Expert submits ground truth feedback for a completed run."""
    run = await db.get(Run, body.run_id)
    if not run or run.institution_id != user.institution_id:
        raise HTTPException(404, "Run not found")

    feedback = ModelFeedback(
        institution_id=user.institution_id,
        evaluation_id=evaluation_id,
        run_id=body.run_id,
        service_id=run.service_id if hasattr(run, "service_id") else _get_service_id(run),
        feedback_type=body.feedback_type,
        original_output=body.original_output or (run.result_manifest or {}),
        corrected_output=body.corrected_output,
        ground_truth=body.ground_truth,
        label_annotations=body.label_annotations,
        quality_score=body.quality_score,
        comments=body.comments,
        included_in_training=False,
        created_by=user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(feedback)
    await db.flush()

    service_id = feedback.service_id
    await _check_and_trigger_training(db, service_id, user.institution_id)

    await db.commit()
    await db.refresh(feedback)
    return FeedbackRead.model_validate(feedback)


@router.get("/runs/{run_id}/feedback", response_model=list[FeedbackRead])
async def get_run_feedback(run_id: uuid.UUID, db: DbSession, user: AuthenticatedUser):
    result = await db.execute(
        select(ModelFeedback).where(
            ModelFeedback.run_id == run_id,
            ModelFeedback.institution_id == user.institution_id,
        ).order_by(ModelFeedback.created_at.desc())
    )
    return [FeedbackRead.model_validate(f) for f in result.scalars().all()]


@router.get("/services/{service_id}/feedback/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    service_id: uuid.UUID,
    db: DbSession,
    user: Annotated[AuthenticatedUser, Depends(require_roles("EXPERT", "ADMIN"))],
):
    """Get feedback statistics for training readiness."""
    total = await db.scalar(
        select(func.count()).where(
            ModelFeedback.service_id == service_id,
            ModelFeedback.institution_id == user.institution_id,
        )
    ) or 0

    unused = await db.scalar(
        select(func.count()).where(
            ModelFeedback.service_id == service_id,
            ModelFeedback.institution_id == user.institution_id,
            ModelFeedback.included_in_training.is_(False),
        )
    ) or 0

    high_quality = await db.scalar(
        select(func.count()).where(
            ModelFeedback.service_id == service_id,
            ModelFeedback.institution_id == user.institution_id,
            ModelFeedback.included_in_training.is_(False),
            ModelFeedback.quality_score >= 0.7,
        )
    ) or 0

    return FeedbackStats(
        service_id=service_id,
        total_feedback=total,
        unused_feedback=unused,
        high_quality_feedback=high_quality,
        ready_for_training=high_quality >= FEEDBACK_THRESHOLD,
        threshold=FEEDBACK_THRESHOLD,
    )


@router.get("/services/{service_id}/feedback", response_model=list[FeedbackRead])
async def list_service_feedback(
    service_id: uuid.UUID,
    db: DbSession,
    user: Annotated[AuthenticatedUser, Depends(require_roles("EXPERT", "ADMIN"))],
    limit: int = Query(default=50, le=200),
    unused_only: bool = Query(default=False),
):
    q = select(ModelFeedback).where(
        ModelFeedback.service_id == service_id,
        ModelFeedback.institution_id == user.institution_id,
    )
    if unused_only:
        q = q.where(ModelFeedback.included_in_training.is_(False))
    q = q.order_by(ModelFeedback.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return [FeedbackRead.model_validate(f) for f in result.scalars().all()]


# ── Training Job endpoints ────────────────────────────────────────────────


@router.post("/services/{service_id}/training-jobs", response_model=TrainingJobRead, status_code=201)
async def create_training_job(
    service_id: uuid.UUID,
    body: TrainingJobCreate,
    db: DbSession,
    user: Annotated[AuthenticatedUser, Depends(require_roles("EXPERT", "ADMIN"))],
):
    """Manually trigger a training job for a service."""
    svc = await db.get(ServiceDefinition, service_id)
    if not svc or svc.institution_id != user.institution_id:
        raise HTTPException(404, "Service not found")

    result = await db.execute(
        select(ModelFeedback).where(
            ModelFeedback.service_id == service_id,
            ModelFeedback.institution_id == user.institution_id,
            ModelFeedback.included_in_training.is_(False),
        ).order_by(ModelFeedback.created_at.asc()).limit(500)
    )
    feedback_list = result.scalars().all()

    if not feedback_list:
        raise HTTPException(400, "No unused feedback available for training")

    job = ModelTrainingJob(
        institution_id=user.institution_id,
        service_id=service_id,
        trigger_type=body.trigger_type,
        status="PENDING",
        feedback_count=len(feedback_list),
        feedback_ids=[str(f.id) for f in feedback_list],
        hyperparameters=body.hyperparameters or {"learning_rate": 1e-4, "epochs": 10, "batch_size": 8},
        created_by=user.id,
    )
    db.add(job)
    await db.flush()

    for f in feedback_list:
        f.included_in_training = True
        f.training_job_id = job.id

    await db.commit()
    await db.refresh(job)

    from app.worker.training_tasks import run_training_job
    task = run_training_job.delay(str(job.id))
    job.celery_task_id = task.id
    await db.commit()

    return TrainingJobRead.model_validate(job)


@router.get("/services/{service_id}/training-jobs", response_model=list[TrainingJobRead])
async def list_training_jobs(
    service_id: uuid.UUID,
    db: DbSession,
    user: Annotated[AuthenticatedUser, Depends(require_roles("EXPERT", "ADMIN"))],
):
    result = await db.execute(
        select(ModelTrainingJob)
        .where(ModelTrainingJob.service_id == service_id,
               ModelTrainingJob.institution_id == user.institution_id)
        .order_by(ModelTrainingJob.created_at.desc())
        .limit(20)
    )
    return [TrainingJobRead.model_validate(j) for j in result.scalars().all()]


@router.get("/training-jobs/{job_id}", response_model=TrainingJobRead)
async def get_training_job(job_id: uuid.UUID, db: DbSession, user: AuthenticatedUser):
    job = await db.get(ModelTrainingJob, job_id)
    if not job or job.institution_id != user.institution_id:
        raise HTTPException(404, "Training job not found")
    return TrainingJobRead.model_validate(job)


# ── Performance Metrics endpoints ─────────────────────────────────────────


@router.get("/services/{service_id}/performance", response_model=PerformanceTimeSeries)
async def get_performance_metrics(
    service_id: uuid.UUID,
    db: DbSession,
    user: AuthenticatedUser,
    days: int = Query(default=30, le=365),
):
    """Get performance metrics time series for a service."""
    from datetime import date, timedelta
    cutoff = date.today() - timedelta(days=days)
    result = await db.execute(
        select(ModelPerformanceMetrics)
        .where(ModelPerformanceMetrics.service_id == service_id,
               ModelPerformanceMetrics.metric_date >= cutoff)
        .order_by(ModelPerformanceMetrics.metric_date.asc())
    )
    data = result.scalars().all()
    return PerformanceTimeSeries(
        service_id=service_id,
        data_points=[PerformanceMetricsRead.model_validate(d) for d in data],
    )


# ── Helper: auto-trigger training ─────────────────────────────────────────


async def _check_and_trigger_training(db, service_id: uuid.UUID, institution_id: uuid.UUID):
    """Check if feedback threshold reached and auto-trigger training."""
    active = await db.scalar(
        select(func.count()).where(
            ModelTrainingJob.service_id == service_id,
            ModelTrainingJob.status.in_(("PENDING", "PREPARING", "TRAINING")),
        )
    )
    if active:
        return

    count = await db.scalar(
        select(func.count()).where(
            ModelFeedback.service_id == service_id,
            ModelFeedback.institution_id == institution_id,
            ModelFeedback.included_in_training.is_(False),
            ModelFeedback.quality_score >= 0.7,
        )
    ) or 0

    if count >= FEEDBACK_THRESHOLD:
        logger.info("Feedback threshold reached for service %s (%d feedbacks), auto-triggering training", service_id, count)
        result = await db.execute(
            select(ModelFeedback).where(
                ModelFeedback.service_id == service_id,
                ModelFeedback.institution_id == institution_id,
                ModelFeedback.included_in_training.is_(False),
                ModelFeedback.quality_score >= 0.7,
            ).limit(500)
        )
        feedback_list = result.scalars().all()

        job = ModelTrainingJob(
            institution_id=institution_id,
            service_id=service_id,
            trigger_type="feedback_threshold",
            status="PENDING",
            feedback_count=len(feedback_list),
            feedback_ids=[str(f.id) for f in feedback_list],
            hyperparameters={"learning_rate": 1e-4, "epochs": 10, "batch_size": 8},
        )
        db.add(job)
        await db.flush()

        for f in feedback_list:
            f.included_in_training = True
            f.training_job_id = job.id

        import asyncio

        async def _dispatch():
            from app.worker.training_tasks import run_training_job
            task = run_training_job.apply_async(args=[str(job.id)], countdown=5)
            job.celery_task_id = task.id
            await db.commit()

        asyncio.create_task(_dispatch())


def _get_service_id(run) -> uuid.UUID:
    """Get service_id from run via request."""
    return run.request.service_id if hasattr(run, "request") and run.request else uuid.uuid4()
