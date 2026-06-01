"""Ingest API schemas."""

from uuid import UUID

from pydantic import Field

from app.schemas.common import SchemaBase


class SyncCreatorRequest(SchemaBase):
    full_backfill: bool = False
    max_videos: int | None = Field(default=None, ge=1, le=500)


class SyncCreatorResponse(SchemaBase):
    job_id: UUID
    creator_id: UUID
    status: str


class IngestWebhookPayload(SchemaBase):
    """Placeholder for platform webhook payloads."""

    platform: str
    event_type: str
    payload: dict
