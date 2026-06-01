"""Ingest videos from URLs: extract, chunk, embed, and index."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

from qdrant_client.http import models as qmodels
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import (
    ChunkType,
    ContentType,
    IngestStatus,
    Platform,
    ProcessingStatus,
    TranscriptSource,
)
from app.db.models.chunk import Chunk
from app.db.models.content_item import ContentItem
from app.db.models.creator import Creator
from app.db.models.transcript import Transcript
from app.domain.engagement import compute_engagement_rate
from app.integrations.extraction.extractor import VideoExtractor
from app.integrations.extraction.models import VideoExtract
from app.integrations.embeddings.client import EmbeddingClient, get_embedding_client
from app.integrations.qdrant.client import QdrantClientWrapper, get_qdrant_client
from app.rag.chunking.strategy import ChunkingStrategy
from app.rag.metadata.schema import ChunkMetadataPayload, EngagementSnapshot


class VideoIngestService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        extractor: VideoExtractor | None = None,
        chunker: ChunkingStrategy | None = None,
        embeddings: EmbeddingClient | None = None,
        qdrant: QdrantClientWrapper | None = None,
    ) -> None:
        self._session = session
        self._extractor = extractor or VideoExtractor()
        self._chunker = chunker or ChunkingStrategy()
        self._embeddings = embeddings or get_embedding_client()
        self._qdrant = qdrant or get_qdrant_client()

    async def create_comparison_creator(
        self,
        org_id: UUID,
        *,
        display_name: str = "URL Comparison",
    ) -> Creator:
        creator = Creator(org_id=org_id, display_name=display_name, ingest_status=IngestStatus.RUNNING)
        self._session.add(creator)
        await self._session.flush()
        return creator

    async def ingest_from_url(
        self,
        *,
        org_id: UUID,
        creator_id: UUID,
        url: str,
        platform: Platform,
    ) -> tuple[ContentItem, VideoExtract]:
        extracted = await self._extractor.extract(url, platform)
        content_hash = hashlib.sha256(
            f"{platform.value}:{extracted.platform_content_id}:{extracted.transcript}".encode()
        ).hexdigest()

        existing = await self._session.execute(
            select(ContentItem).where(
                ContentItem.creator_id == creator_id,
                ContentItem.platform == platform,
                ContentItem.platform_content_id == extracted.platform_content_id,
            )
        )
        content_item = existing.scalar_one_or_none()
        if content_item and content_item.content_hash == content_hash:
            return content_item, extracted

        content_type = ContentType.SHORT if platform == Platform.YOUTUBE else ContentType.REEL
        if content_item is None:
            content_item = ContentItem(
                creator_id=creator_id,
                platform=platform,
                platform_content_id=extracted.platform_content_id,
                content_type=content_type,
            )
            self._session.add(content_item)

        content_item.title = extracted.title
        content_item.description = extracted.description
        content_item.published_at = extracted.upload_date
        content_item.duration_sec = extracted.duration_sec
        content_item.url = extracted.url
        content_item.thumbnail_url = extracted.thumbnail_url
        content_item.content_hash = content_hash
        content_item.processing_status = ProcessingStatus.TRANSCRIBED
        content_item.engagement = {
            "views": extracted.views,
            "likes": extracted.likes,
            "comments": extracted.comments,
            "engagement_rate": extracted.engagement_rate,
            "captured_at": datetime.now(UTC).isoformat(),
        }
        content_item.raw_metadata = {
            "creator_name": extracted.creator_name,
            "hashtags": extracted.hashtags,
        }
        await self._session.flush()

        transcript = Transcript(
            content_item_id=content_item.id,
            source=TranscriptSource.CAPTION,
            language="en",
            text=extracted.transcript,
            segments=extracted.transcript_segments,
            model_version="youtube-transcript-api+yt-dlp",
        )
        self._session.add(transcript)
        await self._session.flush()

        await self._index_content(
            org_id=org_id,
            creator_id=creator_id,
            content_item=content_item,
            transcript=transcript,
            extracted=extracted,
        )
        content_item.processing_status = ProcessingStatus.INDEXED
        await self._session.flush()
        return content_item, extracted

    async def _index_content(
        self,
        *,
        org_id: UUID,
        creator_id: UUID,
        content_item: ContentItem,
        transcript: Transcript,
        extracted: VideoExtract,
    ) -> None:
        upload_iso = extracted.upload_date.isoformat() if extracted.upload_date else None
        raw_chunks = self._chunker.build_all_chunks(
            transcript=extracted.transcript,
            segments=extracted.transcript_segments,
            title=extracted.title,
            description=extracted.description,
            platform=extracted.platform.value,
            creator_name=extracted.creator_name,
            engagement_rate=extracted.engagement_rate,
            views=extracted.views,
            upload_date_iso=upload_iso,
            hashtags=extracted.hashtags,
        )
        if not raw_chunks:
            return

        texts = [chunk.text for chunk in raw_chunks]
        vectors = await self._embeddings.embed_texts(texts)

        points: list[qmodels.PointStruct] = []
        for raw_chunk, vector in zip(raw_chunks, vectors, strict=True):
            chunk_id = uuid4()
            qdrant_point_id = uuid4()
            chunk = Chunk(
                id=chunk_id,
                content_item_id=content_item.id,
                transcript_id=transcript.id,
                chunk_index=raw_chunk.chunk_index,
                chunk_type=ChunkType(raw_chunk.chunk_type),
                text=raw_chunk.text,
                token_count=raw_chunk.token_count,
                qdrant_point_id=qdrant_point_id,
                embedding_model=self._embeddings.model_name,
            )
            self._session.add(chunk)

            payload = ChunkMetadataPayload(
                org_id=org_id,
                creator_id=creator_id,
                content_item_id=content_item.id,
                platform=extracted.platform.value,
                content_type=content_item.content_type.value,
                platform_content_id=extracted.platform_content_id,
                published_at=extracted.upload_date,
                url=extracted.url,
                title=extracted.title,
                description_truncated=(extracted.description or "")[:500],
                duration_sec=extracted.duration_sec,
                language="en",
                chunk_id=chunk_id,
                chunk_index=raw_chunk.chunk_index,
                chunk_type=raw_chunk.chunk_type,
                time_range=raw_chunk.time_range,
                engagement_snapshot=EngagementSnapshot(
                    views=extracted.views,
                    likes=extracted.likes,
                    comments=extracted.comments,
                    captured_at=datetime.now(UTC),
                ),
                hashtags=extracted.hashtags,
                embedding_model=self._embeddings.model_name,
                text_preview=raw_chunk.text[:200],
            )
            points.append(
                qmodels.PointStruct(
                    id=str(qdrant_point_id),
                    vector=vector,
                    payload=payload.to_qdrant_payload(),
                )
            )

        await self._session.flush()
        await self._qdrant.upsert_points(points)

    @staticmethod
    def engagement_summary(extracted: VideoExtract) -> dict:
        return {
            "creator": extracted.creator_name,
            "views": extracted.views,
            "likes": extracted.likes,
            "comments": extracted.comments,
            "upload_date": extracted.upload_date.isoformat() if extracted.upload_date else None,
            "hashtags": extracted.hashtags,
            "engagement_rate": compute_engagement_rate(
                extracted.views,
                extracted.likes,
                extracted.comments,
            ),
        }
