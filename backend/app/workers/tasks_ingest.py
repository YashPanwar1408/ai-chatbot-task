"""Ingest worker tasks."""

from app.domain.exceptions import NotImplementedFeatureError
from app.workers.celery_app import celery_app


@celery_app.task(name="ingest.sync_creator")
def sync_creator_task(job_id: str) -> None:
    raise NotImplementedFeatureError("sync_creator_task")


@celery_app.task(name="ingest.process_webhook")
def process_webhook_task(payload: dict) -> None:
    raise NotImplementedFeatureError("process_webhook_task")
