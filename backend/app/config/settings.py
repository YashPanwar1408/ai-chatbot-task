"""Environment-backed application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "shorts-reels-rag-api"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/shorts_reels_rag"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_stream_prefix: str = "run"
    redis_use_memory: bool = False

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "content_chunks_bge_large_v1_5"
    qdrant_vector_size: int = 1024
    qdrant_use_memory: bool = False

    # Embeddings
    embedding_service_url: str = "http://localhost:8081"
    embedding_model_name: str = "bge-large-en-v1.5"
    embedding_batch_size: int = 32

    # Gemini (key from https://aistudio.google.com/apikey — must start with AIzaSy)
    google_api_key: str | None = None
    # 2.0-flash has higher free-tier RPM than 2.5-flash; override with GEMINI_MODEL
    gemini_model: str = "gemini-2.0-flash"
    # Per-chunk LLM grading uses 1 Gemini call per retrieved chunk (expensive on free tier)
    gemini_llm_grading: bool = False

    # LangGraph
    langgraph_checkpoint_backend: Literal["redis", "postgres"] = "redis"
    graph_version: str = "1.0.0"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_audience: str | None = None
    dev_auth_bypass: bool = True
    default_org_name: str = "Default Organization"

    # RAG
    retrieval_top_k: int = 8
    retrieval_score_threshold: float = 0.35
    grade_min_chunks: int = 2
    chat_memory_ttl_seconds: int = 86400
    chat_memory_max_messages: int = 40

    # External APIs
    youtube_api_key: str | None = None
    instagram_access_token: str | None = None
    # Netscape cookies.txt from a logged-in browser session (helps yt-dlp read play_count)
    instagram_cookies_file: str | None = None

    # Workers
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Observability
    log_level: str = "INFO"
    otel_enabled: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            import json

            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def database_url_async(self) -> str:
        """Async SQLAlchemy URL (asyncpg) without libpq-only query parameters."""
        from app.db.url import ensure_asyncpg_driver

        return ensure_asyncpg_driver(self.database_url)

    @property
    def database_url_sync(self) -> str:
        """Sync SQLAlchemy URL (psycopg2) for Alembic migrations."""
        from app.db.url import ensure_psycopg2_driver

        return ensure_psycopg2_driver(self.database_url)

    @property
    def database_connect_options(self) -> dict[str, str]:
        """libpq options extracted from DATABASE_URL (sslmode, etc.)."""
        from app.db.url import split_database_url

        _, options = split_database_url(self.database_url)
        return options

    @property
    def asyncpg_connect_args(self) -> dict:
        """connect_args for create_async_engine — Neon-compatible SSL."""
        from app.db.url import build_asyncpg_connect_args

        return build_asyncpg_connect_args(self.database_connect_options)


@lru_cache
def get_settings() -> Settings:
    return Settings()
