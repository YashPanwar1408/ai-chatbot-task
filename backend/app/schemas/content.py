"""Content item API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.db.enums import ContentType, Platform, ProcessingStatus
from app.schemas.common import SchemaBase, TimestampSchema


class ContentItemResponse(TimestampSchema):
    id: UUID
    creator_id: UUID
    platform: Platform
    platform_content_id: str
    content_type: ContentType
    title: str | None
    description: str | None
    published_at: datetime | None
    duration_sec: int | None
    url: str | None
    thumbnail_url: str | None
    engagement: dict | None
    processing_status: ProcessingStatus


class ContentListParams(SchemaBase):
    platform: Platform | None = None
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
