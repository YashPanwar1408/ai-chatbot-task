"""Normalize media metadata values from external APIs."""

from typing import Any


def normalize_duration_sec(value: Any) -> int | None:
    """
    yt-dlp returns duration as float seconds (e.g. 49.689 for Instagram Reels).
    Database columns and Qdrant payloads expect integers.
    """
    if value is None:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return int(round(seconds))
