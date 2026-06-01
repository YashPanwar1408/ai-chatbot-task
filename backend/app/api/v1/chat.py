"""Chat session routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import AuthContext, get_auth, get_run_service
from app.domain.services.run_service import RunService
from app.schemas.chat import ChatMessageCreate, ChatMessageResponse, ChatSessionCreate, ChatSessionResponse

router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: ChatSessionCreate,
    auth: AuthContext = Depends(get_auth),
    service: RunService = Depends(get_run_service),
) -> ChatSessionResponse:
    run = await service.create_chat_session(auth.org_id, body)
    return ChatSessionResponse(id=run.id, creator_id=body.creator_id, title=body.title)


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: UUID,
    body: ChatMessageCreate,
    auth: AuthContext = Depends(get_auth),
    service: RunService = Depends(get_run_service),
) -> ChatMessageResponse:
    run = await service.send_chat_message(auth.org_id, session_id, body)
    return ChatMessageResponse(run_id=run.id, status=run.status)
