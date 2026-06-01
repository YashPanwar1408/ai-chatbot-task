"""Normalized video extraction result."""

from dataclasses import dataclass, field
from datetime import datetime

from app.db.enums import Platform


@dataclass
class VideoExtract:
    platform: Platform
    url: str
    platform_content_id: str
    creator_name: str
    title: str
    description: str
    transcript: str
    transcript_segments: list[dict]
    views: int | None
    likes: int | None
    comments: int | None
    upload_date: datetime | None
    hashtags: list[str] = field(default_factory=list)
    engagement_rate: float = 0.0
    duration_sec: int | None = None
    thumbnail_url: str | None = None
