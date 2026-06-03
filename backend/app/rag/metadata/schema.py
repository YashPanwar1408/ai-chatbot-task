"""Qdrant payload metadata schema."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.media import normalize_duration_sec

METADATA_SCHEMA_VERSION = "1.0"


class EngagementSnapshot(BaseModel):
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    captured_at: datetime | None = None


class TimeRange(BaseModel):
    start_sec: float
    end_sec: float


class ChunkMetadataPayload(BaseModel):
    """Payload stored in Qdrant alongside vectors."""

    schema_version: str = METADATA_SCHEMA_VERSION
    org_id: UUID
    creator_id: UUID
    content_item_id: UUID
    platform: Literal["youtube", "instagram"]
    content_type: Literal["short", "reel"]
    platform_content_id: str
    published_at: datetime | None = None
    url: str | None = None
    title: str | None = None
    description_truncated: str | None = None
    duration_sec: int | None = None
    language: str | None = None
    chunk_id: UUID
    chunk_index: int
    chunk_type: Literal["transcript", "caption", "metadata", "hashtag_block", "hook"]
    time_range: TimeRange | None = None
    engagement_snapshot: EngagementSnapshot | None = None
    hashtags: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)
    audio_present: bool | None = None
    embedding_model: str
    ingest_job_id: UUID | None = None
    text_preview: str | None = None

    @field_validator("duration_sec", mode="before")
    @classmethod
    def coerce_duration_sec(cls, value: object) -> int | None:
        if value is None or isinstance(value, int):
            return value
        return normalize_duration_sec(value)

    def to_qdrant_payload(self) -> dict:
        return self.model_dump(mode="json")
