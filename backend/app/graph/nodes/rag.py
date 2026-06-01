"""Core RAG LangGraph nodes: retrieve, grade, generate, cite."""

from __future__ import annotations

import json
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from app.config.settings import get_settings
from app.graph.state import ChatGraphState, ChunkHitState
from app.integrations.gemini.client import get_gemini_client
from app.integrations.redis.client import get_redis_client
from app.rag.retrieval.service import RetrievalService

_settings = get_settings()
_retrieval = RetrievalService()
_gemini = get_gemini_client()
_redis = get_redis_client()


def _hits_to_state(hits) -> list[ChunkHitState]:
    return [
        {
            "chunk_id": str(hit.chunk_id),
            "content_item_id": str(hit.content_item_id),
            "score": hit.score,
            "text_preview": hit.text_preview,
            "payload": hit.payload,
        }
        for hit in hits
    ]


async def load_memory(state: ChatGraphState) -> dict:
    session_id = state.get("session_id")
    if not session_id:
        return {"phase": "load_memory"}
    history = await _redis.get_chat_memory(UUID(session_id))
    messages = []
    for item in history:
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        else:
            messages.append(AIMessage(content=item["content"]))
    return {"phase": "load_memory", "messages": messages}


async def rewrite_query(state: ChatGraphState) -> dict:
    query = state.get("user_query", "")
    history = state.get("messages") or []
    if not history:
        return {"phase": "rewrite_query", "rewritten_query": query}

    history_text = "\n".join(
        f"{message.type}: {message.content}"
        for message in history[-6:]
        if getattr(message, "content", None)
    )
    prompt = (
        "Rewrite the latest user question into a standalone search query using prior context.\n"
        f"Conversation:\n{history_text}\n\n"
        f"Latest question: {query}\n"
        "Return only the rewritten query."
    )
    rewritten = await _gemini.generate(prompt)
    return {"phase": "rewrite_query", "rewritten_query": rewritten.strip() or query}


async def retrieve(state: ChatGraphState) -> dict:
    org_id = UUID(state["org_id"])
    creator_id = UUID(state["creator_id"])
    query = state.get("rewritten_query") or state.get("user_query", "")
    filters = state.get("filters") or {}
    attempts = int(state.get("retrieval_attempts", 0)) + 1
    limit = _settings.retrieval_top_k if attempts == 1 else _settings.retrieval_top_k * 2

    hits = await _retrieval.retrieve(
        org_id=org_id,
        creator_id=creator_id,
        query=query,
        limit=limit,
        filters=filters,
    )
    run_id = state.get("run_id")
    if run_id:
        await _redis.publish_stream_event(
            UUID(run_id),
            "status",
            {"phase": "retrieve", "chunks": len(hits)},
        )
    return {
        "phase": "retrieve",
        "retrieved_chunks": _hits_to_state(hits),
        "retrieval_attempts": attempts,
    }


async def grade_documents(state: ChatGraphState) -> dict:
    query = state.get("rewritten_query") or state.get("user_query", "")
    retrieved = state.get("retrieved_chunks") or []
    graded: list[ChunkHitState] = []

    for chunk in retrieved:
        score = float(chunk.get("score", 0.0))
        text = str(chunk.get("text_preview", ""))
        is_relevant = score >= _settings.retrieval_score_threshold
        if is_relevant and _settings.google_api_key:
            try:
                is_relevant = await _gemini.grade_relevance(query, text)
            except Exception:
                is_relevant = score >= _settings.retrieval_score_threshold
        if is_relevant:
            graded.append(chunk)

    run_id = state.get("run_id")
    if run_id:
        await _redis.publish_stream_event(
            UUID(run_id),
            "status",
            {"phase": "grade", "graded": len(graded)},
        )
    return {"phase": "grade_documents", "graded_chunks": graded}


async def generate(state: ChatGraphState) -> dict:
    query = state.get("user_query", "")
    chunks = state.get("graded_chunks") or state.get("retrieved_chunks") or []
    context_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        payload = chunk.get("payload", {})
        platform = payload.get("platform", "unknown")
        url = payload.get("url", "")
        context_blocks.append(
            f"[{index}] platform={platform} url={url}\n{chunk.get('text_preview', '')}"
        )
    context = "\n\n".join(context_blocks) or "No retrieved context."
    system = (
        "You compare YouTube Shorts and Instagram Reels using only provided context. "
        "If context is insufficient, say so clearly."
    )
    prompt = f"Question:\n{query}\n\nContext:\n{context}\n\nAnswer with concise analysis."

    run_id = state.get("run_id")
    tokens: list[str] = []
    if run_id:
        async for delta in _gemini.generate_stream(prompt, system=system):
            tokens.append(delta)
            await _redis.publish_stream_event(
                UUID(run_id),
                "token",
                {"delta": delta},
            )
        answer = "".join(tokens)
    else:
        answer = await _gemini.generate(prompt, system=system)

    return {
        "phase": "generate",
        "draft_answer": answer,
        "messages": [AIMessage(content=answer)],
    }


async def cite(state: ChatGraphState) -> dict:
    chunks = state.get("graded_chunks") or state.get("retrieved_chunks") or []
    citations: list[dict] = []
    for rank, chunk in enumerate(chunks[:10], start=1):
        payload = chunk.get("payload", {})
        citation = {
            "rank": rank,
            "chunk_id": chunk.get("chunk_id"),
            "content_item_id": chunk.get("content_item_id"),
            "score": chunk.get("score"),
            "platform": payload.get("platform"),
            "url": payload.get("url"),
            "title": payload.get("title"),
            "text_preview": chunk.get("text_preview"),
        }
        citations.append(citation)
        run_id = state.get("run_id")
        if run_id:
            await _redis.publish_stream_event(UUID(run_id), "citation", citation)

    return {"phase": "cite", "citations": citations}


async def save_memory(state: ChatGraphState) -> dict:
    session_id = state.get("session_id")
    if not session_id:
        return {"phase": "save_memory"}

    user_query = state.get("user_query", "")
    answer = state.get("draft_answer", "")
    session_uuid = UUID(session_id)
    await _redis.append_chat_memory(session_uuid, "user", user_query)
    await _redis.append_chat_memory(session_uuid, "assistant", answer)
    return {"phase": "save_memory"}
