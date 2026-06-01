"""Organization bootstrap for development and first-run."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.enums import PlanTier, UserRole
from app.db.models.organization import Organization
from app.db.models.user import User


class OrgService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()

    async def get_or_create_default_org(self) -> tuple[Organization, User]:
        result = await self._session.execute(
            select(Organization).where(Organization.name == self._settings.default_org_name)
        )
        org = result.scalar_one_or_none()
        if org is None:
            org = Organization(name=self._settings.default_org_name, plan_tier=PlanTier.FREE)
            self._session.add(org)
            await self._session.flush()

        user_result = await self._session.execute(
            select(User).where(User.org_id == org.id).limit(1)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            user = User(
                org_id=org.id,
                email=f"dev-{uuid4().hex[:8]}@local.dev",
                role=UserRole.OWNER,
            )
            self._session.add(user)
            await self._session.flush()

        return org, user

    async def resolve_org_id(self, org_id: UUID | None) -> UUID:
        if org_id is not None:
            return org_id
        org, _user = await self.get_or_create_default_org()
        return org.id
