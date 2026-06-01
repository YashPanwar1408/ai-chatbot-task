"""Conditional edge predicates for LangGraph."""

from app.config.settings import get_settings
from app.graph.state import GraphState

_settings = get_settings()


def documents_relevant(state: GraphState) -> str:
    """Route after grading: sufficient context vs expand retrieval."""
    graded = state.get("graded_chunks") or []
    attempts = int(state.get("retrieval_attempts", 0))
    if len(graded) >= _settings.grade_min_chunks or attempts >= 2:
        return "sufficient"
    return "insufficient"


def compare_has_enough_context(state: GraphState) -> str:
    return documents_relevant(state)
