"""Usage quota routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import AuthContext, get_auth, get_usage_service
from app.domain.services.usage_service import UsageService
from app.schemas.usage import UsageDailyResponse

router = APIRouter()


@router.get("", response_model=UsageDailyResponse)
async def get_usage(
    auth: AuthContext = Depends(get_auth),
    service: UsageService = Depends(get_usage_service),
) -> UsageDailyResponse:
    usage = await service.get_daily_usage(auth.org_id)
    if usage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usage not found")
    return UsageDailyResponse.model_validate(usage)
