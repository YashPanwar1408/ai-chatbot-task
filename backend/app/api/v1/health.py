"""Health and readiness endpoints."""

from fastapi import APIRouter, Depends

from app.integrations.qdrant.client import QdrantClientWrapper
from app.integrations.redis.client import RedisClient
from app.api.deps import get_qdrant, get_redis
from app.schemas.common import HealthResponse, ReadyResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
async def ready(
    redis: RedisClient = Depends(get_redis),
    qdrant: QdrantClientWrapper = Depends(get_qdrant),
) -> ReadyResponse:
    postgres_ok = True  # TODO: execute SELECT 1 via session
    redis_ok = await redis.health_check()
    qdrant_ok = await qdrant.health_check()
    status = "ok" if all([postgres_ok, redis_ok, qdrant_ok]) else "degraded"
    return ReadyResponse(
        status=status,
        postgres=postgres_ok,
        redis=redis_ok,
        qdrant=qdrant_ok,
    )
