"""Content item domain service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import Platform
from app.db.models.content_item import ContentItem
from app.db.models.creator import Creator
from app.domain.exceptions import NotFoundError
from app.domain.types import PaginatedResult
from app.schemas.content import ContentListParams


class ContentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, org_id: UUID, content_id: UUID) -> ContentItem:
        result = await self._session.execute(
            select(ContentItem)
            .join(Creator, ContentItem.creator_id == Creator.id)
            .where(ContentItem.id == content_id, Creator.org_id == org_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundError("content_item", str(content_id))
        return item

    async def list_for_creator(
        self,
        org_id: UUID,
        creator_id: UUID,
        params: ContentListParams,
    ) -> PaginatedResult[ContentItem]:
        query = (
            select(ContentItem)
            .join(Creator, ContentItem.creator_id == Creator.id)
            .where(ContentItem.creator_id == creator_id, Creator.org_id == org_id)
        )
        if params.platform is not None:
            query = query.where(ContentItem.platform == Platform(params.platform))
        query = query.order_by(ContentItem.published_at.desc().nullslast()).limit(params.limit + 1)
        result = await self._session.execute(query)
        rows = list(result.scalars().all())
        next_cursor = None
        if len(rows) > params.limit:
            rows = rows[: params.limit]
            next_cursor = str(rows[-1].id)
        return PaginatedResult(items=rows, next_cursor=next_cursor, total=len(rows))
