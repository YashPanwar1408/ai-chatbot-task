"""Chat API schemas."""

from uuid import UUID

from pydantic import Field

from app.db.enums import AnalysisRunStatus
from app.schemas.common import SchemaBase, TimestampSchema
from app.schemas.compare import CompareFilters


class ChatSessionCreate(SchemaBase):
    creator_id: UUID
    title: str | None = Field(default=None, max_length=255)


class ChatSessionResponse(TimestampSchema):
    id: UUID
    creator_id: UUID
    title: str | None


class ChatMessageCreate(SchemaBase):
    message: str = Field(..., min_length=1, max_length=4000)
    filters: CompareFilters | None = None


class ChatMessageResponse(SchemaBase):
    run_id: UUID
    status: AnalysisRunStatus
