"""FastAPI dependencies."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.session import get_async_session
from app.domain.services.compare_service import CompareService
from app.domain.services.content_service import ContentService
from app.domain.services.creator_service import CreatorService
from app.domain.services.ingest_service import IngestService
from app.domain.services.job_service import JobService
from app.domain.services.org_service import OrgService
from app.domain.services.run_service import RunService
from app.domain.services.usage_service import UsageService
from app.integrations.qdrant.client import QdrantClientWrapper, get_qdrant_client
from app.integrations.redis.client import RedisClient, get_redis_client


@dataclass
class AuthContext:
    """Authenticated request context."""

    user_id: UUID
    org_id: UUID


async def get_db(session: AsyncSession = Depends(get_async_session)) -> AsyncSession:
    return session


async def get_auth(
    session: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> AuthContext:
    settings = get_settings()
    org_service = OrgService(session)

    if settings.dev_auth_bypass:
        org, user = await org_service.get_or_create_default_org()
        if x_org_id:
            try:
                org_id = UUID(x_org_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid X-Org-Id") from exc
        else:
            org_id = org.id
        return AuthContext(user_id=user.id, org_id=org_id)

    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication not implemented",
    )


def get_creator_service(session: AsyncSession = Depends(get_db)) -> CreatorService:
    return CreatorService(session)


def get_content_service(session: AsyncSession = Depends(get_db)) -> ContentService:
    return ContentService(session)


def get_ingest_service(session: AsyncSession = Depends(get_db)) -> IngestService:
    return IngestService(session)


def get_compare_service(session: AsyncSession = Depends(get_db)) -> CompareService:
    return CompareService(session)


def get_run_service(session: AsyncSession = Depends(get_db)) -> RunService:
    return RunService(session)


def get_job_service(session: AsyncSession = Depends(get_db)) -> JobService:
    return JobService(session)


def get_usage_service(session: AsyncSession = Depends(get_db)) -> UsageService:
    return UsageService(session)


async def get_redis() -> AsyncGenerator[RedisClient, None]:
    client = get_redis_client()
    await client.connect()
    try:
        yield client
    finally:
        pass


def get_qdrant() -> QdrantClientWrapper:
    return get_qdrant_client()
