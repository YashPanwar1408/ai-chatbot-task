"""Engagement metrics calculations."""


def compute_engagement_rate(
    views: int | None,
    likes: int | None,
    comments: int | None,
) -> float:
    """
    Engagement rate as (likes + comments) / views * 100.

    Returns 0.0 when views are missing or zero.
    """
    view_count = views or 0
    if view_count <= 0:
        return 0.0
    interactions = (likes or 0) + (comments or 0)
    return round((interactions / view_count) * 100.0, 4)
