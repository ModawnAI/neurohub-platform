from celery import Celery
from kombu import Exchange, Queue

from app.config import settings

celery_app = Celery(
    "neurohub",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Queue definitions
# - default:   general tasks with no specific resource requirements
# - compute:   container execution (CPU-bound, short-lived)
# - inference: GPU model inference runs (Phase B)
# - training:  GPU fine-tuning jobs (Phase C)
# - builder:   Docker image builds for expert models
# - scanner:   Security scans (Trivy, Bandit, etc.)
# - reporting: Report/PDF generation and webhook delivery
NEUROHUB_QUEUES = (
    Queue("default",   Exchange("default"),   routing_key="default"),
    Queue("compute",   Exchange("compute"),   routing_key="compute"),
    Queue("inference", Exchange("inference"), routing_key="inference"),
    Queue("training",  Exchange("training"),  routing_key="training"),
    Queue("builder",   Exchange("builder"),   routing_key="builder"),
    Queue("scanner",   Exchange("scanner"),   routing_key="scanner"),
    Queue("reporting", Exchange("reporting"), routing_key="reporting"),
)

celery_app.conf.update(
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_transport_options={"visibility_timeout": 3600},
    task_queues=NEUROHUB_QUEUES,
    task_default_queue="default",
    task_routes={
        "neurohub.tasks.execute_run": {"queue": "compute"},
        "neurohub.tasks.generate_report": {"queue": "reporting"},
        "neurohub.tasks.generate_pdf_report": {"queue": "reporting"},
        "neurohub.tasks.deliver_webhook": {"queue": "reporting"},
        "neurohub.tasks.auto_cancel_stale_requests": {"queue": "compute"},
        "neurohub.tasks.apply_watermark": {"queue": "compute"},
        # Phase B: inference queue for direct container jobs
        "neurohub.tasks.execute_inference_job": {"queue": "inference"},
        # Phase C placeholders
        "neurohub.tasks.execute_training_job": {"queue": "training"},
        "neurohub.tasks.build_expert_image": {"queue": "builder"},
        "neurohub.tasks.scan_image": {"queue": "scanner"},
    },
    beat_schedule={
        "auto-cancel-stale-requests": {
            "task": "neurohub.tasks.auto_cancel_stale_requests",
            "schedule": 3600.0,  # every hour
        },
    },
    # Ensure all task modules are discovered
    include=["app.worker.tasks", "app.worker.pipeline", "app.services.stale_cleanup"],
)
