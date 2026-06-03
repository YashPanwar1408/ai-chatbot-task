"""Database URL normalization for asyncpg (Neon) and psycopg2 (Alembic)."""

from __future__ import annotations

import ssl
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# libpq query params — must not be passed to asyncpg.connect()
LIBPQ_ONLY_QUERY_PARAMS = frozenset(
    {
        "sslmode",
        "channel_binding",
        "sslcert",
        "sslkey",
        "sslrootcert",
        "sslcrl",
        "sslcompression",
        "sslsni",
    }
)


def split_database_url(url: str) -> tuple[str, dict[str, str]]:
    """
    Return (sqlalchemy_url_without_libpq_params, libpq_connect_options).

    Neon URLs often include ?sslmode=require&channel_binding=require which
    asyncpg rejects as unexpected keyword arguments.
    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)

    connect_options: dict[str, str] = {}
    filtered_query: dict[str, list[str]] = {}
    for key, values in query.items():
        key_lower = key.lower()
        if key_lower in LIBPQ_ONLY_QUERY_PARAMS and values:
            connect_options[key_lower] = values[-1]
        elif values:
            filtered_query[key] = values

    clean = parsed._replace(query=urlencode(filtered_query, doseq=True))
    return urlunparse(clean), connect_options


def ensure_asyncpg_driver(url: str) -> str:
    """Ensure URL uses the asyncpg SQLAlchemy driver."""
    base, _opts = split_database_url(url)
    if base.startswith("postgresql+asyncpg://"):
        return base
    if base.startswith("postgresql+psycopg2://"):
        return base.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if base.startswith("postgresql://"):
        return base.replace("postgresql://", "postgresql+asyncpg://", 1)
    if base.startswith("postgres://"):
        return base.replace("postgres://", "postgresql+asyncpg://", 1)
    return base


def ensure_psycopg2_driver(url: str) -> str:
    """Ensure URL uses the psycopg2 SQLAlchemy driver for sync Alembic migrations."""
    base, opts = split_database_url(url)
    if base.startswith("postgresql+psycopg2://"):
        return f"{base}?{urlencode(opts, doseq=True)}" if opts else base
    if base.startswith("postgresql+asyncpg://"):
        base = base.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    elif base.startswith("postgresql://"):
        base = base.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif base.startswith("postgres://"):
        base = base.replace("postgres://", "postgresql+psycopg2://", 1)
    # psycopg2 understands sslmode in the query string
    if opts:
        separator = "&" if "?" in base else "?"
        base = f"{base}{separator}{urlencode(opts, doseq=True)}"
    return base


def build_asyncpg_connect_args(connect_options: dict[str, str]) -> dict[str, Any]:
    """
    Map libpq sslmode to asyncpg's ``ssl`` connect argument.

    Neon requires TLS; ``sslmode=require`` → SSL context with encryption enabled.
    """
    sslmode = (connect_options.get("sslmode") or "require").lower()
    if sslmode == "disable":
        return {}

    if sslmode in ("require", "prefer", "allow"):
        # Neon serverless: encrypt without local CA bundle requirement
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return {"ssl": ctx}

    if sslmode in ("verify-ca", "verify-full"):
        return {"ssl": ssl.create_default_context()}

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return {"ssl": ctx}
