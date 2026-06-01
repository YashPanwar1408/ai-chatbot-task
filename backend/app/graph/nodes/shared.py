"""Shared LangGraph nodes."""

from app.graph.state import GraphState


async def grade_documents(state: GraphState) -> dict:
    """Grade retrieved chunks for relevance. Stub."""
    return {"phase": "grade_documents", "graded_chunks": state.get("retrieved_chunks", [])}
