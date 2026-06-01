"""Background job domain service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job import Job
from app.domain.exceptions import NotFoundError


class JobService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_job(self, org_id: UUID, job_id: UUID) -> Job:
        result = await self._session.execute(
            select(Job).where(Job.id == job_id, Job.org_id == org_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise NotFoundError("job", str(job_id))
        return job
