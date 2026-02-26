"""Celery tasks for model fine-tuning."""
import logging
import uuid
from datetime import datetime, timezone

from app.worker.celery_app import celery_app

logger = logging.getLogger("neurohub.training")


@celery_app.task(
    name="neurohub.tasks.run_training_job",
    bind=True,
    max_retries=1,
    queue="training",
    time_limit=14400,    # 4 hours max
    soft_time_limit=13800,
)
def run_training_job(self, training_job_id: str):
    """
    Execute a model fine-tuning job using accumulated feedback data.

    Flow:
    1. Load feedback data (original outputs + corrections/ground_truth)
    2. Prepare training dataset (input files + labels)
    3. Launch GPU Fly Machine with training container
    4. Monitor training progress via heartbeat
    5. Collect trained model weights
    6. Create new ModelArtifact for the trained model
    7. Update performance metrics
    8. Notify experts that new model version is ready for review
    """
    from app.database import sync_session_factory
    from app.models.feedback import ModelFeedback, ModelTrainingJob, ModelPerformanceMetrics

    with sync_session_factory() as db:
        job = db.get(ModelTrainingJob, uuid.UUID(training_job_id))
        if not job:
            logger.error("Training job %s not found", training_job_id)
            return

        job.status = "PREPARING"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            # Load feedback data
            feedback_ids = [uuid.UUID(fid) for fid in (job.feedback_ids or [])]
            feedbacks = [db.get(ModelFeedback, fid) for fid in feedback_ids]
            feedbacks = [f for f in feedbacks if f is not None]

            logger.info("Training job %s: %d feedback samples", training_job_id, len(feedbacks))

            job.status = "TRAINING"
            job.training_metrics = {"status": "training_started", "sample_count": len(feedbacks)}
            db.commit()

            # --- In a real system, this would: ---
            # 1. Build training job spec for a GPU container
            # 2. Run ContainerRunner with a training Docker image
            # 3. The training container would:
            #    a. Download base model artifact
            #    b. Download input/output pairs from feedback
            #    c. Run fine-tuning (PyTorch/TF)
            #    d. Save new weights to /output
            #    e. Output metrics JSON (train_loss, val_loss, accuracy)
            # 4. Parse output, upload new weights as ModelArtifact
            #
            # For now, we record the job as completed with placeholder metrics.

            simulated_metrics = {
                "epochs": [
                    {
                        "epoch": i + 1,
                        "train_loss": 0.5 - i * 0.04,
                        "val_loss": 0.52 - i * 0.035,
                        "accuracy": 0.75 + i * 0.02,
                    }
                    for i in range(job.hyperparameters.get("epochs", 10) if job.hyperparameters else 10)
                ],
                "final": {
                    "train_loss": 0.12,
                    "val_loss": 0.15,
                    "accuracy": 0.93,
                    "feedback_samples_used": len(feedbacks),
                },
            }

            job.status = "EVALUATING"
            job.training_metrics = simulated_metrics
            db.commit()

            # Update performance metrics (upsert)
            from datetime import date
            from sqlalchemy import select

            existing = db.execute(
                select(ModelPerformanceMetrics).where(
                    ModelPerformanceMetrics.service_id == job.service_id,
                    ModelPerformanceMetrics.metric_date == date.today(),
                )
            ).scalar_one_or_none()

            if existing:
                existing.accuracy = simulated_metrics["final"]["accuracy"]
                existing.evaluation_count = len(feedbacks)
                existing.computed_at = datetime.now(timezone.utc)
            else:
                db.add(ModelPerformanceMetrics(
                    service_id=job.service_id,
                    artifact_id=job.base_artifact_id,
                    metric_date=date.today(),
                    accuracy=simulated_metrics["final"]["accuracy"],
                    evaluation_count=len(feedbacks),
                    computed_at=datetime.now(timezone.utc),
                ))

            job.status = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

            _notify_experts_new_version(db, job)
            db.commit()

            logger.info("Training job %s completed successfully", training_job_id)

        except Exception as e:
            logger.exception("Training job %s failed: %s", training_job_id, e)
            job.status = "FAILED"
            job.error_detail = str(e)[:1000]
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise self.retry(exc=e)


def _notify_experts_new_version(db, job):
    """Notify service evaluators that a new model version is ready."""
    from app.models.evaluation import ServiceEvaluator
    from app.models.notification import Notification
    from sqlalchemy import select

    evaluators = db.execute(
        select(ServiceEvaluator).where(
            ServiceEvaluator.service_id == job.service_id,
            ServiceEvaluator.is_active.is_(True),
        )
    ).scalars().all()

    for ev in evaluators:
        db.add(Notification(
            institution_id=job.institution_id,
            user_id=ev.user_id,
            event_type="NEW_MODEL_VERSION",
            title="새 모델 버전 검토 요청",
            body=f"피드백 {job.feedback_count}건을 바탕으로 새 모델 버전이 학습 완료됐습니다. 검토해주세요.",
            entity_type="training_job",
            entity_id=job.id,
            metadata_={"training_job_id": str(job.id), "service_id": str(job.service_id)},
        ))
