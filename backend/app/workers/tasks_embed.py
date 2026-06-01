"""Embedding and Qdrant indexing worker tasks."""

from app.domain.exceptions import NotImplementedFeatureError
from app.workers.celery_app import celery_app


@celery_app.task(name="embed.batch_embed_content")
def batch_embed_content_task(content_item_id: str) -> None:
    raise NotImplementedFeatureError("batch_embed_content_task")


@celery_app.task(name="embed.reindex_creator")
def reindex_creator_task(creator_id: str) -> None:
    raise NotImplementedFeatureError("reindex_creator_task")
