"""OpenTelemetry tracing setup (stub)."""

from app.config.settings import get_settings
from app.domain.exceptions import NotImplementedFeatureError


def configure_tracing() -> None:
    settings = get_settings()
    if not settings.otel_enabled:
        return
    raise NotImplementedFeatureError("configure_tracing")
