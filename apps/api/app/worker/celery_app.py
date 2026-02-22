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
    },
)
