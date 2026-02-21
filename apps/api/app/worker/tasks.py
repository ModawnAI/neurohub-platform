import logging

from app.worker.celery_app import celery_app

logger = logging.getLogger("neurohub.worker")


@celery_app.task(name="neurohub.tasks.execute_run")
def execute_run(run_id: str):
    # TODO: connect with GPU pipeline executor.
    logger.info("Execute run requested: %s", run_id)
    return {"run_id": run_id, "status": "accepted"}

