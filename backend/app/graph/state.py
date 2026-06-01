"""LangGraph shared state definitions."""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ChunkHitState(TypedDict, total=False):
    chunk_id: str
    content_item_id: str
    score: float
    text_preview: str
    payload: dict


class GraphState(TypedDict, total=False):
    """Shared state for compare and chat graphs."""

    run_id: str
    session_id: str
    org_id: str
    creator_id: str
    user_query: str
    rewritten_query: str
    compare_template_id: str | None
    filters: dict
    retrieved_chunks: list[ChunkHitState]
    graded_chunks: list[ChunkHitState]
    platform_aggregates: dict
    draft_answer: str
    citations: list[dict]
    messages: Annotated[list[BaseMessage], add_messages]
    errors: list[str]
    token_usage: dict
    phase: str
    retrieval_attempts: int


class CompareGraphState(GraphState, total=False):
    sub_queries: list[str]
    structured_output: dict


class ChatGraphState(GraphState, total=False):
    pass
