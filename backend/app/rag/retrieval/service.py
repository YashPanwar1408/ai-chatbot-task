"""Retrieval orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.config.settings import get_settings
from app.integrations.embeddings.client import EmbeddingClient, get_embedding_client
from app.integrations.qdrant.client import QdrantClientWrapper, get_qdrant_client


@dataclass
class ChunkHit:
    chunk_id: UUID
    content_item_id: UUID
    score: float
    text_preview: str
    payload: dict


class RetrievalService:
    """Dense retrieval with tenant filters."""

    def __init__(
        self,
        qdrant: QdrantClientWrapper | None = None,
        embeddings: EmbeddingClient | None = None,
    ) -> None:
        self._qdrant = qdrant or get_qdrant_client()
        self._embeddings = embeddings or get_embedding_client()
        self._settings = get_settings()

    def _to_hits(self, points) -> list[ChunkHit]:
        hits: list[ChunkHit] = []
        for point in points:
            payload = point.payload or {}
            chunk_id = payload.get("chunk_id")
            content_item_id = payload.get("content_item_id")
            if not chunk_id or not content_item_id:
                continue
            hits.append(
                ChunkHit(
                    chunk_id=UUID(str(chunk_id)),
                    content_item_id=UUID(str(content_item_id)),
                    score=float(point.score or 0.0),
                    text_preview=str(payload.get("text_preview") or ""),
                    payload=payload,
                )
            )
        return hits

    async def retrieve(
        self,
        *,
        org_id: UUID,
        creator_id: UUID,
        query: str,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> list[ChunkHit]:
        limit = limit or self._settings.retrieval_top_k
        query_vector = await self._embeddings.embed_query(query)
        points = await self._qdrant.search(
            query_vector,
            org_id=org_id,
            creator_id=creator_id,
            limit=limit,
            filter_extra=filters,
        )
        return self._to_hits(points)

    async def parallel_retrieve(
        self,
        *,
        org_id: UUID,
        creator_id: UUID,
        queries: list[str],
        limit_per_query: int = 5,
        filters: dict | None = None,
    ) -> list[ChunkHit]:
        merged: dict[str, ChunkHit] = {}
        for query in queries:
            hits = await self.retrieve(
                org_id=org_id,
                creator_id=creator_id,
                query=query,
                limit=limit_per_query,
                filters=filters,
            )
            for hit in hits:
                key = str(hit.chunk_id)
                existing = merged.get(key)
                if existing is None or hit.score > existing.score:
                    merged[key] = hit
        return sorted(merged.values(), key=lambda item: item.score, reverse=True)
