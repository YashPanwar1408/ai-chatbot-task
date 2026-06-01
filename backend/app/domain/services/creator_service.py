"""Creator domain service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.creator import Creator
from app.domain.exceptions import NotFoundError
from app.domain.types import PaginatedResult
from app.schemas.creator import CreatorCreate, CreatorUpdate


class CreatorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, org_id: UUID, data: CreatorCreate) -> Creator:
        creator = Creator(
            org_id=org_id,
            display_name=data.display_name,
            youtube_channel_id=data.youtube_channel_id,
            instagram_user_id=data.instagram_user_id,
            metadata_=data.metadata,
        )
        self._session.add(creator)
        await self._session.flush()
        return creator

    async def get_by_id(self, org_id: UUID, creator_id: UUID) -> Creator:
        result = await self._session.execute(
            select(Creator).where(Creator.id == creator_id, Creator.org_id == org_id)
        )
        creator = result.scalar_one_or_none()
        if creator is None:
            raise NotFoundError("creator", str(creator_id))
        return creator

    async def list(
        self,
        org_id: UUID,
        *,
        cursor: str | None,
        limit: int,
    ) -> PaginatedResult[Creator]:
        query = (
            select(Creator)
            .where(Creator.org_id == org_id)
            .order_by(Creator.created_at.desc())
            .limit(limit + 1)
        )
        result = await self._session.execute(query)
        rows = list(result.scalars().all())
        next_cursor = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = str(rows[-1].id)
        return PaginatedResult(items=rows, next_cursor=next_cursor, total=len(rows))

    async def update(self, org_id: UUID, creator_id: UUID, data: CreatorUpdate) -> Creator:
        creator = await self.get_by_id(org_id, creator_id)
        if data.display_name is not None:
            creator.display_name = data.display_name
        if data.youtube_channel_id is not None:
            creator.youtube_channel_id = data.youtube_channel_id
        if data.instagram_user_id is not None:
            creator.instagram_user_id = data.instagram_user_id
        if data.metadata is not None:
            creator.metadata_ = data.metadata
        await self._session.flush()
        return creator

    async def delete(self, org_id: UUID, creator_id: UUID) -> None:
        creator = await self.get_by_id(org_id, creator_id)
        await self._session.delete(creator)
        await self._session.flush()
