"""Analysis run and SSE streaming routes."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse

from app.api.deps import AuthContext, get_auth, get_run_service
from app.domain.services.run_service import RunService
from app.schemas.run import RunResponse, StreamEvent

router = APIRouter()


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    auth: AuthContext = Depends(get_auth),
    service: RunService = Depends(get_run_service),
) -> RunResponse:
    run = await service.get_run(auth.org_id, run_id)
    return RunResponse.model_validate(run)


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: UUID,
    auth: AuthContext = Depends(get_auth),
    service: RunService = Depends(get_run_service),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    async def event_generator():
        async for event in service.stream_events(
            auth.org_id,
            run_id,
            last_event_id=last_event_id,
        ):
            payload = json.dumps(event.data)
            yield f"event: {event.event.value}\ndata: {payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
