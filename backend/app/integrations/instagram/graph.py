"""Optional Instagram Graph API enrichment for owned media."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.instagram.com/v21.0"
PLAY_METRICS = frozenset({"plays", "views", "video_views", "impressions", "reach"})


def _normalize_permalink(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}".lower()


def _views_from_insights(insights: dict | list | None) -> int | None:
    if not insights:
        return None
    rows = insights.get("data", insights) if isinstance(insights, dict) else insights
    if not isinstance(rows, list):
        return None
    for row in rows:
        name = str(row.get("name", "")).lower()
        if name not in PLAY_METRICS:
            continue
        values = row.get("values") or []
        if values:
            value = values[0].get("value")
            if value is not None:
                return int(value)
        value = row.get("value")
        if value is not None:
            return int(value)
    return None


async def fetch_views_for_reel_url(access_token: str, reel_url: str) -> int | None:
    """
    Fetch play/view count for a Reel URL using an Instagram User access token.

    Only works when the Reel belongs to the Instagram account connected to the token.
    Public third-party Reels are not available via the official Graph API.
    """
    target = _normalize_permalink(reel_url)
    shortcode = target.rstrip("/").split("/")[-1]

    async with httpx.AsyncClient(timeout=30.0) as client:
        after: str | None = None
        for _ in range(20):
            params: dict[str, str | int] = {
                "fields": "id,permalink,media_type,insights.metric(plays,views,reach)",
                "access_token": access_token,
                "limit": 50,
            }
            if after:
                params["after"] = after

            response = await client.get(f"{GRAPH_BASE}/me/media", params=params)
            if response.status_code != 200:
                logger.debug(
                    "Instagram Graph media list failed: %s %s",
                    response.status_code,
                    response.text[:300],
                )
                return None

            payload = response.json()
            for item in payload.get("data", []):
                permalink = _normalize_permalink(item.get("permalink") or "")
                media_id = str(item.get("id", ""))
                if not permalink and not media_id:
                    continue
                if shortcode not in permalink and shortcode not in media_id:
                    continue

                views = _views_from_insights(item.get("insights"))
                if views is not None:
                    return views

                if media_id:
                    detail = await client.get(
                        f"{GRAPH_BASE}/{media_id}",
                        params={
                            "fields": "insights.metric(plays,views,reach)",
                            "access_token": access_token,
                        },
                    )
                    if detail.status_code == 200:
                        views = _views_from_insights(detail.json().get("insights"))
                        if views is not None:
                            return views

            after = (payload.get("paging") or {}).get("cursors", {}).get("after")
            if not after:
                break

    return None
