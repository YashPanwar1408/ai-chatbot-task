"""In-process vector store when Qdrant is not running (local dev without Docker)."""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID

from qdrant_client.http import models as qmodels


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _payload_matches(payload: dict[str, Any], query_filter: qmodels.Filter | None) -> bool:
    if query_filter is None or not query_filter.must:
        return True
    for condition in query_filter.must:
        if not isinstance(condition, qmodels.FieldCondition):
            continue
        key = condition.key
        match = condition.match
        if not isinstance(match, qmodels.MatchValue):
            continue
        if str(payload.get(key, "")) != str(match.value):
            return False
    return True


class InMemoryQdrantStore:
    """Minimal Qdrant-compatible store for upsert + filtered vector search."""

    def __init__(self, vector_size: int) -> None:
        self.vector_size = vector_size
        self._points: dict[str, tuple[list[float], dict[str, Any] | None]] = {}

    async def collection_exists(self, _collection_name: str) -> bool:
        return True

    async def create_collection(self, *_args, **_kwargs) -> None:
        return None

    async def create_payload_index(self, *_args, **_kwargs) -> None:
        return None

    async def upsert(self, _collection_name: str, points: list[qmodels.PointStruct]) -> None:
        for point in points:
            vector = list(point.vector) if point.vector is not None else []
            self._points[str(point.id)] = (vector, point.payload)

    async def delete(self, *_args, **_kwargs) -> None:
        return None

    async def query_points(
        self,
        _collection_name: str,
        *,
        query: list[float],
        query_filter: qmodels.Filter | None = None,
        limit: int = 10,
        with_payload: bool = True,
        **_kwargs: Any,
    ) -> qmodels.QueryResponse:
        scored: list[qmodels.ScoredPoint] = []
        query_vector = list(query)
        for point_id, (vector, payload) in self._points.items():
            payload = payload or {}
            if not _payload_matches(payload, query_filter):
                continue
            score = _cosine_similarity(query_vector, vector)
            scored.append(
                qmodels.ScoredPoint(
                    id=point_id,
                    version=0,
                    score=score,
                    payload=payload if with_payload else None,
                )
            )
        scored.sort(key=lambda item: float(item.score or 0.0), reverse=True)
        return qmodels.QueryResponse(points=scored[:limit])

    async def get_collections(self) -> object:
        return None

    async def close(self) -> None:
        return None
