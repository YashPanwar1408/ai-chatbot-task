"""Database package."""

from app.db.base import Base

__all__ = ["Base", "async_session_factory", "get_async_session"]


def __getattr__(name: str):
    """Lazy import session so Alembic can load models without creating the async engine."""
    if name in {"async_session_factory", "get_async_session"}:
        from app.db import session as session_module

        return getattr(session_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
