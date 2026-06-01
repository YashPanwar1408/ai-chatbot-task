"""Ingest webhook routes."""

from fastapi import APIRouter, Depends, status

from app.api.deps import get_ingest_service
from app.domain.services.ingest_service import IngestService
from app.schemas.common import MessageResponse
from app.schemas.ingest import IngestWebhookPayload

router = APIRouter()


@router.post("/ingest/webhook", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_webhook(
    body: IngestWebhookPayload,
    service: IngestService = Depends(get_ingest_service),
) -> MessageResponse:
    await service.handle_webhook(body.model_dump())
    return MessageResponse(message="Webhook accepted")
