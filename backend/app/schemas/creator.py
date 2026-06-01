"""Creator API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.db.enums import IngestStatus
from app.schemas.common import SchemaBase, TimestampSchema


class CreatorCreate(SchemaBase):
    display_name: str = Field(..., min_length=1, max_length=255)
    youtube_channel_id: str | None = None
    instagram_user_id: str | None = None
    metadata: dict | None = None


class CreatorUpdate(SchemaBase):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    youtube_channel_id: str | None = None
    instagram_user_id: str | None = None
    metadata: dict | None = None


class CreatorResponse(TimestampSchema):
    id: UUID
    org_id: UUID
    display_name: str
    youtube_channel_id: str | None
    instagram_user_id: str | None
    ingest_status: IngestStatus
    last_synced_at: datetime | None
    metadata: dict | None = Field(default=None, validation_alias="metadata_")
