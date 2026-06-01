"""Analysis run and streaming API schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from app.db.enums import AnalysisRunStatus, RunType
from app.schemas.common import SchemaBase, TimestampSchema


class RunResponse(TimestampSchema):
    id: UUID
    org_id: UUID
    creator_id: UUID
    run_type: RunType
    query: str | None
    status: AnalysisRunStatus
    graph_version: str | None
    token_usage: dict | None
    result_summary: dict | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None


class StreamEventType(str, Enum):
    STATUS = "status"
    TOKEN = "token"
    CITATION = "citation"
    METRIC = "metric"
    DONE = "done"
    ERROR = "error"


class StreamEvent(SchemaBase):
    event: StreamEventType
    data: dict
