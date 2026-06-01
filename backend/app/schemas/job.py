"""Job API schemas."""

from uuid import UUID

from app.db.enums import JobStatus, JobType
from app.schemas.common import SchemaBase, TimestampSchema


class JobResponse(TimestampSchema):
    id: UUID
    org_id: UUID
    job_type: JobType
    payload: dict | None
    status: JobStatus
    progress_pct: int
    celery_task_id: str | None
    error: dict | None
