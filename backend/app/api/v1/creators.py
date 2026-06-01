"""Creator CRUD routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from app.api.deps import AuthContext, get_auth, get_creator_service, get_ingest_service
from app.domain.services.creator_service import CreatorService
from app.domain.services.ingest_service import IngestService
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.creator import CreatorCreate, CreatorResponse, CreatorUpdate
from app.schemas.ingest import SyncCreatorRequest, SyncCreatorResponse

router = APIRouter()


@router.post("", response_model=CreatorResponse, status_code=status.HTTP_201_CREATED)
async def create_creator(
    body: CreatorCreate,
    auth: AuthContext = Depends(get_auth),
    service: CreatorService = Depends(get_creator_service),
) -> CreatorResponse:
    creator = await service.create(auth.org_id, body)
    return CreatorResponse.model_validate(creator)


@router.get("", response_model=PaginatedResponse[CreatorResponse])
async def list_creators(
    cursor: str | None = None,
    limit: int = 20,
    auth: AuthContext = Depends(get_auth),
    service: CreatorService = Depends(get_creator_service),
) -> PaginatedResponse[CreatorResponse]:
    page = await service.list(auth.org_id, cursor=cursor, limit=limit)
    return PaginatedResponse(
        items=[CreatorResponse.model_validate(item) for item in page.items],
        next_cursor=page.next_cursor,
        total=page.total,
    )


@router.get("/{creator_id}", response_model=CreatorResponse)
async def get_creator(
    creator_id: UUID,
    auth: AuthContext = Depends(get_auth),
    service: CreatorService = Depends(get_creator_service),
) -> CreatorResponse:
    creator = await service.get_by_id(auth.org_id, creator_id)
    return CreatorResponse.model_validate(creator)


@router.patch("/{creator_id}", response_model=CreatorResponse)
async def update_creator(
    creator_id: UUID,
    body: CreatorUpdate,
    auth: AuthContext = Depends(get_auth),
    service: CreatorService = Depends(get_creator_service),
) -> CreatorResponse:
    creator = await service.update(auth.org_id, creator_id, body)
    return CreatorResponse.model_validate(creator)


@router.delete("/{creator_id}", response_model=MessageResponse)
async def delete_creator(
    creator_id: UUID,
    auth: AuthContext = Depends(get_auth),
    service: CreatorService = Depends(get_creator_service),
) -> MessageResponse:
    await service.delete(auth.org_id, creator_id)
    return MessageResponse(message="Creator deletion enqueued")


@router.post("/{creator_id}/sync", response_model=SyncCreatorResponse)
async def sync_creator(
    creator_id: UUID,
    body: SyncCreatorRequest,
    auth: AuthContext = Depends(get_auth),
    ingest: IngestService = Depends(get_ingest_service),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> SyncCreatorResponse:
    job = await ingest.enqueue_sync(
        auth.org_id,
        creator_id,
        body,
        idempotency_key=idempotency_key,
    )
    return SyncCreatorResponse(job_id=job.id, creator_id=creator_id, status=job.status.value)
