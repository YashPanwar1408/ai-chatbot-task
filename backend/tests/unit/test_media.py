from app.domain.media import normalize_duration_sec


def test_normalize_duration_sec_rounds_float() -> None:
    assert normalize_duration_sec(49.689) == 50


def test_normalize_duration_sec_integer() -> None:
    assert normalize_duration_sec(28) == 28


def test_normalize_duration_sec_none() -> None:
    assert normalize_duration_sec(None) is None
