"""Qdrant vector database client wrapper."""

from __future__ import annotations

from functools import lru_cache
from typing import Any
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.config.settings import Settings, get_settings
from app.domain.exceptions import IntegrationError


class QdrantClientWrapper:
    """Thin async wrapper around Qdrant operations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = AsyncQdrantClient(
            url=self._settings.qdrant_url,
            api_key=self._settings.qdrant_api_key,
        )
        self.collection_name = self._settings.qdrant_collection_name
        self.vector_size = self._settings.qdrant_vector_size

    @property
    def client(self) -> AsyncQdrantClient:
        return self._client

    async def ensure_collection(self) -> None:
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
            await self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field_name,
                field_schema=field_schema,
            )

    async def upsert_points(self, points: list[qmodels.PointStruct]) -> None:
        if not points:
            return
        await self.ensure_collection()
        await self._client.upsert(collection_name=self.collection_name, points=points)

    async def delete_by_filter(self, filter_conditions: qmodels.Filter) -> None:
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
        return await self._client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

    async def health_check(self) -> bool:
        try:
            await self._client.get_collections()
            return True
        except Exception as exc:
            raise IntegrationError("qdrant", str(exc)) from exc

    async def close(self) -> None:
        await self._client.close()


@lru_cache
def get_qdrant_client() -> QdrantClientWrapper:
    return QdrantClientWrapper()
