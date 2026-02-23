from celery import Celery

from app.config import settings

celery_app = Celery(
    "neurohub",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_transport_options={"visibility_timeout": 3600},
    task_routes={
        "neurohub.tasks.execute_run": {"queue": "compute"},
        "neurohub.tasks.generate_report": {"queue": "reporting"},
        "neurohub.tasks.auto_cancel_stale_requests": {"queue": "compute"},
    },
    beat_schedule={
        "auto-cancel-stale-requests": {
            "task": "neurohub.tasks.auto_cancel_stale_requests",
            "schedule": 3600.0,  # every hour
        },
    },
    # Ensure stale_cleanup task module is discovered
    include=["app.services.stale_cleanup"],
)
