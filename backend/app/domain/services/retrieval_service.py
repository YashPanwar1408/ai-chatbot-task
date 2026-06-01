"""Domain-facing retrieval facade."""

from uuid import UUID

from app.rag.retrieval.service import ChunkHit, RetrievalService


class RetrievalDomainService:
    def __init__(self, retrieval: RetrievalService | None = None) -> None:
        self._retrieval = retrieval or RetrievalService()

    async def search_creator_corpus(
        self,
        *,
        org_id: UUID,
        creator_id: UUID,
        query: str,
        limit: int = 10,
        filters: dict | None = None,
    ) -> list[ChunkHit]:
        return await self._retrieval.retrieve(
            org_id=org_id,
            creator_id=creator_id,
            query=query,
            limit=limit,
            filters=filters,
        )
