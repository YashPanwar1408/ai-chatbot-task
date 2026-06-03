"""Qdrant vector database client wrapper with in-memory fallback."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.config.settings import Settings, get_settings
from app.domain.exceptions import IntegrationError
from app.integrations.qdrant.memory_store import InMemoryQdrantStore

logger = logging.getLogger(__name__)


class QdrantClientWrapper:
    """Async wrapper around Qdrant or an in-memory fallback for local dev."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self.collection_name = self._settings.qdrant_collection_name
        self.vector_size = self._settings.qdrant_vector_size
        self._memory = InMemoryQdrantStore(self.vector_size)
        self._client: AsyncQdrantClient | None = None
        self._use_memory = self._settings.qdrant_use_memory
        if not self._use_memory:
            self._client = AsyncQdrantClient(
                url=self._settings.qdrant_url,
                api_key=self._settings.qdrant_api_key,
            )

    @property
    def using_memory(self) -> bool:
        return self._use_memory

    async def _activate_memory_fallback(self, exc: Exception | None = None) -> None:
        if self._use_memory:
            return
        self._use_memory = True
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None
        reason = str(exc) if exc else "unavailable"
        logger.warning("Qdrant unavailable (%s); using in-memory vector store", reason)

    async def _remote_ok(self) -> bool:
        if self._use_memory or self._client is None:
            return False
        try:
            await self._client.get_collections()
            return True
        except Exception as exc:
            await self._activate_memory_fallback(exc)
            return False

    @property
    def client(self) -> AsyncQdrantClient:
        if self._use_memory or self._client is None:
            raise IntegrationError("qdrant", "Remote Qdrant client not active (memory fallback)")
        return self._client

    async def ensure_collection(self) -> None:
        if self._use_memory:
            await self._memory.create_collection()
            return
        if not await self._remote_ok():
            await self._memory.create_collection()
            return

        exists = await self._client.collection_exists(self.collection_name)
        if not exists:
            await self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self.vector_size,
                    distance=qmodels.Distance.COSINE,
                ),
            )

        for field_name, field_schema in (
            ("org_id", qmodels.PayloadSchemaType.KEYWORD),
            ("creator_id", qmodels.PayloadSchemaType.KEYWORD),
            ("platform", qmodels.PayloadSchemaType.KEYWORD),
            ("content_item_id", qmodels.PayloadSchemaType.KEYWORD),
            ("chunk_type", qmodels.PayloadSchemaType.KEYWORD),
        ):
            try:
                await self._client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                )
            except Exception:
                pass

    async def upsert_points(self, points: list[qmodels.PointStruct]) -> None:
        if not points:
            return
        await self.ensure_collection()
        if self._use_memory:
            await self._memory.upsert(self.collection_name, points)
            return
        try:
            await self._client.upsert(collection_name=self.collection_name, points=points)
        except Exception as exc:
            await self._activate_memory_fallback(exc)
            await self._memory.upsert(self.collection_name, points)

    async def delete_by_filter(self, filter_conditions: qmodels.Filter) -> None:
        if self._use_memory:
            return
        if not await self._remote_ok():
            return
        await self._client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.FilterSelector(filter=filter_conditions),
        )

    def _build_filter(
        self,
        *,
        org_id: UUID,
        creator_id: UUID,
        filter_extra: dict[str, Any] | None = None,
    ) -> qmodels.Filter:
        must: list[qmodels.Condition] = [
            qmodels.FieldCondition(
                key="org_id",
                match=qmodels.MatchValue(value=str(org_id)),
            ),
            qmodels.FieldCondition(
                key="creator_id",
                match=qmodels.MatchValue(value=str(creator_id)),
            ),
        ]
        if filter_extra:
            platform = filter_extra.get("platform")
            if platform:
                must.append(
                    qmodels.FieldCondition(
                        key="platform",
                        match=qmodels.MatchValue(value=str(platform)),
                    )
                )
        return qmodels.Filter(must=must)

    async def search(
        self,
        query_vector: list[float],
        *,
        org_id: UUID,
        creator_id: UUID,
        limit: int = 10,
        filter_extra: dict[str, Any] | None = None,
    ) -> list[qmodels.ScoredPoint]:
        await self.ensure_collection()
        query_filter = self._build_filter(
            org_id=org_id,
            creator_id=creator_id,
            filter_extra=filter_extra,
        )
        if self._use_memory:
            response = await self._memory.query_points(
                self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            return list(response.points)

        try:
            response = await self._client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            return list(response.points)
        except Exception as exc:
            await self._activate_memory_fallback(exc)
            response = await self._memory.query_points(
                self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            return list(response.points)

    async def health_check(self) -> bool:
        if self._use_memory:
            return True
        try:
            await self._client.get_collections()
            return True
        except Exception as exc:
            raise IntegrationError("qdrant", str(exc)) from exc

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
        await self._memory.close()


@lru_cache
def get_qdrant_client() -> QdrantClientWrapper:
    return QdrantClientWrapper()
