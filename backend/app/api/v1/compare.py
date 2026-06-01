"""Compare analysis routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import AuthContext, get_auth, get_compare_service
from app.domain.services.compare_service import CompareService
from app.schemas.compare import (
    CompareCreateRequest,
    CompareCreateResponse,
    CompareResultResponse,
    CompareUrlsRequest,
    CompareUrlsResponse,
    VideoPlatformSummary,
)

router = APIRouter()


@router.post("/urls", response_model=CompareUrlsResponse, status_code=status.HTTP_201_CREATED)
async def compare_urls(
    body: CompareUrlsRequest,
    auth: AuthContext = Depends(get_auth),
    service: CompareService = Depends(get_compare_service),
) -> CompareUrlsResponse:
    result = await service.ingest_urls(auth.org_id, body)
    return CompareUrlsResponse(
        creator_id=result["creator_id"],
        youtube=VideoPlatformSummary(**result["youtube"]),
        instagram=VideoPlatformSummary(**result["instagram"]),
        run_id=result.get("run_id"),
        run_status=result.get("run_status"),
    )


@router.post("", response_model=CompareCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_compare(
    body: CompareCreateRequest,
    auth: AuthContext = Depends(get_auth),
    service: CompareService = Depends(get_compare_service),
) -> CompareCreateResponse:
    run = await service.start_compare(auth.org_id, body)
    return CompareCreateResponse(run_id=run.id, status=run.status)


@router.get("/{run_id}", response_model=CompareResultResponse)
async def get_compare(
    run_id: UUID,
    auth: AuthContext = Depends(get_auth),
    service: CompareService = Depends(get_compare_service),
) -> CompareResultResponse:
    run = await service.get_result(auth.org_id, run_id)
    return CompareResultResponse(
        id=run.id,
        creator_id=run.creator_id,
        status=run.status,
        result_summary=run.result_summary,
        citations=(run.result_summary or {}).get("citations"),
        error=run.error,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )
