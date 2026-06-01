from app.domain.engagement import compute_engagement_rate


def test_engagement_rate() -> None:
    assert compute_engagement_rate(1000, 50, 10) == 6.0


def test_engagement_rate_zero_views() -> None:
    assert compute_engagement_rate(0, 50, 10) == 0.0
