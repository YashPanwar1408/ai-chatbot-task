"""LangGraph execution worker tasks."""

from app.domain.exceptions import NotImplementedFeatureError
from app.workers.celery_app import celery_app


@celery_app.task(name="graph.run_compare")
def run_compare_graph_task(run_id: str) -> None:
    raise NotImplementedFeatureError("run_compare_graph_task")


@celery_app.task(name="graph.run_chat")
def run_chat_graph_task(run_id: str) -> None:
    raise NotImplementedFeatureError("run_chat_graph_task")
