"""Content item routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import AuthContext, get_auth, get_content_service
from app.db.enums import Platform
from app.domain.services.content_service import ContentService
from app.schemas.common import PaginatedResponse
from app.schemas.content import ContentItemResponse, ContentListParams

router = APIRouter()


@router.get("/creators/{creator_id}/content", response_model=PaginatedResponse[ContentItemResponse])
async def list_creator_content(
    creator_id: UUID,
    platform: Platform | None = None,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    auth: AuthContext = Depends(get_auth),
    service: ContentService = Depends(get_content_service),
) -> PaginatedResponse[ContentItemResponse]:
    params = ContentListParams(platform=platform, cursor=cursor, limit=limit)
    page = await service.list_for_creator(auth.org_id, creator_id, params)
    return PaginatedResponse(
        items=[ContentItemResponse.model_validate(item) for item in page.items],
        next_cursor=page.next_cursor,
        total=page.total,
    )


@router.get("/content/{content_id}", response_model=ContentItemResponse)
async def get_content(
    content_id: UUID,
    auth: AuthContext = Depends(get_auth),
    service: ContentService = Depends(get_content_service),
) -> ContentItemResponse:
    item = await service.get_by_id(auth.org_id, content_id)
    return ContentItemResponse.model_validate(item)
