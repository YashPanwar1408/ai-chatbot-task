"""Compare analysis API schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from app.db.enums import AnalysisRunStatus
from app.schemas.common import SchemaBase, TimestampSchema


class CompareTemplate(str, Enum):
    POSTING_CADENCE = "posting_cadence"
    HOOK_PATTERNS = "hook_patterns"
    TOPIC_OVERLAP = "topic_overlap"
    ENGAGEMENT_EFFICIENCY = "engagement_efficiency"
    CUSTOM = "custom"


class CompareFilters(SchemaBase):
    date_from: datetime | None = None
    date_to: datetime | None = None
    platforms: list[str] | None = None
    limit_per_platform: int | None = Field(default=None, ge=1, le=50)


class CompareUrlsRequest(SchemaBase):
    youtube_url: str = Field(..., min_length=10)
    instagram_url: str = Field(..., min_length=10)
    display_name: str | None = None
    query: str | None = None
    filters: CompareFilters | None = None


class VideoPlatformSummary(SchemaBase):
    content_id: UUID
    creator: str
    views: int | None
    likes: int | None
    comments: int | None
    upload_date: str | None
    hashtags: list[str]
    engagement_rate: float
    transcript_preview: str | None = None


class CompareUrlsResponse(SchemaBase):
    creator_id: UUID
    youtube: VideoPlatformSummary
    instagram: VideoPlatformSummary
    run_id: UUID | None = None
    run_status: AnalysisRunStatus | None = None


class CompareCreateRequest(SchemaBase):
    creator_id: UUID
    template: CompareTemplate | None = None
    query: str | None = None
    filters: CompareFilters | None = None


class CompareCreateResponse(SchemaBase):
    run_id: UUID
    status: AnalysisRunStatus


class CompareDimension(SchemaBase):
    name: str
    youtube_summary: str | None = None
    instagram_summary: str | None = None
    winner: str | None = None


class CompareResultResponse(TimestampSchema):
    id: UUID
    creator_id: UUID
    status: AnalysisRunStatus
    result_summary: dict | None = None
    dimensions: list[CompareDimension] | None = None
    citations: list[dict] | None = None
    error: str | None = None
