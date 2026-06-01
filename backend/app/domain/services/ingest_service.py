"""Ingest and sync domain service."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import JobStatus, JobType
from app.db.models.job import Job
from app.domain.exceptions import NotImplementedFeatureError
from app.schemas.ingest import SyncCreatorRequest


class IngestService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue_sync(
        self,
        org_id: UUID,
        creator_id: UUID,
        request: SyncCreatorRequest,
        *,
        idempotency_key: str | None,
    ) -> Job:
        job = Job(
            org_id=org_id,
            job_type=JobType.SYNC_CREATOR,
            payload={
                "creator_id": str(creator_id),
                "full_backfill": request.full_backfill,
                "max_videos": request.max_videos,
            },
            status=JobStatus.PENDING,
            idempotency_key=idempotency_key,
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def handle_webhook(self, payload: dict) -> None:
        raise NotImplementedFeatureError("IngestService.handle_webhook")
