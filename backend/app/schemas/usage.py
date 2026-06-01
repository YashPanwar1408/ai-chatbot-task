"""Usage quota API schemas."""

from datetime import date
from uuid import UUID

from app.schemas.common import SchemaBase


class UsageDailyResponse(SchemaBase):
    org_id: UUID
    date: date
    creators_synced: int
    videos_ingested: int
    embed_tokens: int
    llm_input_tokens: int
    llm_output_tokens: int
