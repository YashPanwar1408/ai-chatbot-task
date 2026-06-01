"""Background job routes."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import AuthContext, get_auth, get_job_service
from app.domain.services.job_service import JobService
from app.schemas.job import JobResponse

router = APIRouter()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    auth: AuthContext = Depends(get_auth),
    service: JobService = Depends(get_job_service),
) -> JobResponse:
    job = await service.get_job(auth.org_id, job_id)
    return JobResponse.model_validate(job)
