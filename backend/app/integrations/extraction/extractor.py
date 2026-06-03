"""Extract metadata and transcripts from YouTube Shorts and Instagram Reels."""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from youtube_transcript_api import YouTubeTranscriptApi

from app.db.enums import Platform
from app.config.settings import get_settings
from app.domain.engagement import compute_engagement_rate
from app.domain.media import normalize_duration_sec
from app.domain.exceptions import IntegrationError, ValidationError
from app.integrations.extraction.models import VideoExtract

HASHTAG_PATTERN = re.compile(r"#\w+")
YOUTUBE_ID_PATTERN = re.compile(
    r"(?:youtube\.com/(?:shorts/|watch\?v=)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def _detect_platform(url: str) -> Platform:
    host = urlparse(url).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return Platform.YOUTUBE
    if "instagram.com" in host:
        return Platform.INSTAGRAM
    raise ValidationError(f"Unsupported URL host: {host}")


def _extract_hashtags(text: str, extra_tags: list[str] | None = None) -> list[str]:
    found = {tag.lower() for tag in HASHTAG_PATTERN.findall(text or "")}
    for tag in extra_tags or []:
        normalized = tag if tag.startswith("#") else f"#{tag}"
        found.add(normalized.lower())
    return sorted(found)


def _parse_count(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip().lower()
        multiplier = 1
        if cleaned.endswith("k"):
            multiplier = 1_000
            cleaned = cleaned[:-1]
        elif cleaned.endswith("m"):
            multiplier = 1_000_000
            cleaned = cleaned[:-1]
        elif cleaned.endswith("b"):
            multiplier = 1_000_000_000
            cleaned = cleaned[:-1]
        try:
            return int(float(cleaned) * multiplier)
        except ValueError:
            return None
    return None


def _youtube_video_id(url: str) -> str:
    match = YOUTUBE_ID_PATTERN.search(url)
    if match:
        return match.group(1)
    raise ValidationError("Could not parse YouTube video id from URL")


def _fetch_youtube_transcript(video_id: str) -> tuple[str, list[dict]]:
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(["en", "en-US", "en-GB"])
        if transcript.is_translatable:
            transcript = transcript.translate("en")
        segments = transcript.fetch()
    except Exception:
        return "", []

    parts: list[str] = []
    normalized_segments: list[dict] = []
    for segment in segments:
        text = segment.get("text", "").strip()
        if not text:
            continue
        parts.append(text)
        normalized_segments.append(
            {
                "start": segment.get("start"),
                "end": segment.get("duration"),
                "text": text,
            }
        )
    return " ".join(parts).strip(), normalized_segments


def _instagram_view_count(info: dict[str, Any]) -> int | None:
    """yt-dlp field names vary; Instagram often omits views without cookies."""
    for key in (
        "view_count",
        "play_count",
        "video_view_count",
        "video_play_count",
        "view_count_raw",
        "views",
        "plays",
        "view",
        "video_views",
        "like_count",
        "comment_count",
        "stats",
        "statistics",
    ):
        value = info.get(key)
        if isinstance(value, dict):
            # Sometimes stats/statistics might be a dict, check for any numeric value for views/plays
            for subkey in ("view_count", "play_count", "views", "plays", "video_views", "video_view_count"):
                if subkey in value:
                    parsed = _parse_count(value[subkey])
                    if parsed is not None:
                        return parsed
        parsed = _parse_count(value)
        if parsed is not None:
            return parsed
    return None


def _run_yt_dlp(url: str) -> dict[str, Any]:
    import yt_dlp

    settings = get_settings()
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    if settings.instagram_cookies_file:
        options["cookiefile"] = settings.instagram_cookies_file
    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=False)


def _normalize_yt_dlp(platform: Platform, url: str, info: dict[str, Any]) -> VideoExtract:
    platform_content_id = str(info.get("id") or "")
    if not platform_content_id:
        raise IntegrationError("yt-dlp", "Missing content id in extraction response")

    description = info.get("description") or ""
    title = info.get("title") or ""
    tags = [str(tag) for tag in (info.get("tags") or [])]
    hashtags = _extract_hashtags(f"{title}\n{description}", tags)

    upload_date_raw = info.get("upload_date")
    upload_date: datetime | None = None
    if upload_date_raw:
        upload_date = datetime.strptime(str(upload_date_raw), "%Y%m%d").replace(tzinfo=UTC)

    views = _parse_count(info.get("view_count"))
    if platform == Platform.INSTAGRAM:
        views = views or _instagram_view_count(info)
    likes = _parse_count(info.get("like_count"))
    comments = _parse_count(info.get("comment_count"))

    transcript = ""
    segments: list[dict] = []
    if platform == Platform.YOUTUBE:
        transcript, segments = _fetch_youtube_transcript(platform_content_id)
    if not transcript:
        subtitles = info.get("subtitles") or {}
        automatic_captions = info.get("automatic_captions") or {}
        caption_sources = {**subtitles, **automatic_captions}
        for lang_key in ("en", "en-US", "en-orig"):
            entries = caption_sources.get(lang_key)
            if entries:
                transcript = f"Captions available ({lang_key}); fetch via dedicated parser in production."
                break
    if not transcript:
        transcript = description[:2000] if description else title

    engagement_rate = compute_engagement_rate(views, likes, comments)
    creator_name = (
        info.get("channel")
        or info.get("uploader")
        or info.get("uploader_id")
        or "unknown"
    )

    return VideoExtract(
        platform=platform,
        url=url,
        platform_content_id=platform_content_id,
        creator_name=str(creator_name),
        title=str(title),
        description=str(description),
        transcript=transcript,
        transcript_segments=segments,
        views=views,
        likes=likes,
        comments=comments,
        upload_date=upload_date,
        hashtags=hashtags,
        engagement_rate=engagement_rate,
        duration_sec=normalize_duration_sec(info.get("duration")),
        thumbnail_url=info.get("thumbnail"),
    )


class VideoExtractor:
    """Async facade over yt-dlp and platform-specific transcript APIs."""

    async def extract(self, url: str, platform: Platform | None = None) -> VideoExtract:
        resolved_platform = platform or _detect_platform(url)
        if resolved_platform == Platform.YOUTUBE:
            _youtube_video_id(url)

        try:
            info = await asyncio.to_thread(_run_yt_dlp, url)
        except Exception as exc:
            raise IntegrationError("yt-dlp", str(exc)) from exc

        extracted = _normalize_yt_dlp(resolved_platform, url, info)
        if resolved_platform == Platform.INSTAGRAM and extracted.views is None:
            extracted = await self._enrich_instagram_views(extracted)
        return extracted

    async def _enrich_instagram_views(self, extracted: VideoExtract) -> VideoExtract:
        from app.integrations.instagram.graph import fetch_views_for_reel_url

        settings = get_settings()
        token = settings.instagram_access_token
        if not token:
            return extracted

        try:
            views = await fetch_views_for_reel_url(token, extracted.url)
        except Exception:
            return extracted

        if views is None:
            return extracted

        return VideoExtract(
            platform=extracted.platform,
            url=extracted.url,
            platform_content_id=extracted.platform_content_id,
            creator_name=extracted.creator_name,
            title=extracted.title,
            description=extracted.description,
            transcript=extracted.transcript,
            transcript_segments=extracted.transcript_segments,
            views=views,
            likes=extracted.likes,
            comments=extracted.comments,
            upload_date=extracted.upload_date,
            hashtags=extracted.hashtags,
            engagement_rate=compute_engagement_rate(
                views, extracted.likes, extracted.comments
            ),
            duration_sec=extracted.duration_sec,
            thumbnail_url=extracted.thumbnail_url,
        )

    async def extract_youtube(self, url: str) -> VideoExtract:
        return await self.extract(url, Platform.YOUTUBE)

    async def extract_instagram(self, url: str) -> VideoExtract:
        return await self.extract(url, Platform.INSTAGRAM)
