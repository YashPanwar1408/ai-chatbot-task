"""LangGraph checkpoint backends."""

from app.domain.exceptions import NotImplementedFeatureError


def get_checkpointer():
    """Return configured LangGraph checkpointer (Redis or Postgres)."""
    raise NotImplementedFeatureError("get_checkpointer")
