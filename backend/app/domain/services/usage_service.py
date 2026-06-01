"""Usage quota domain service."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.usage_daily import UsageDaily
from app.domain.exceptions import NotImplementedFeatureError


class UsageService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_daily_usage(self, org_id: UUID) -> UsageDaily | None:
        raise NotImplementedFeatureError("UsageService.get_daily_usage")
