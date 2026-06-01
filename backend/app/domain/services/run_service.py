"""Analysis run, chat, and streaming domain service."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.enums import AnalysisRunStatus, RunType
from app.db.models.analysis_run import AnalysisRun
from app.db.session import async_session_factory
from app.domain.exceptions import NotFoundError
from app.domain.services.graph_runner_service import GraphRunnerService
from app.integrations.redis.client import get_redis_client
from app.schemas.chat import ChatMessageCreate, ChatSessionCreate
from app.schemas.run import StreamEvent, StreamEventType


class RunService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()
        self._redis = get_redis_client()

    async def get_run(self, org_id: UUID, run_id: UUID) -> AnalysisRun:
        result = await self._session.execute(
            select(AnalysisRun).where(AnalysisRun.id == run_id, AnalysisRun.org_id == org_id)
        )
        run = result.scalar_one_or_none()
        if run is None:
            raise NotFoundError("analysis_run", str(run_id))
        return run

    async def create_chat_session(self, org_id: UUID, data: ChatSessionCreate) -> AnalysisRun:
        session = AnalysisRun(
            org_id=org_id,
            creator_id=data.creator_id,
            run_type=RunType.CHAT,
            query=data.title or "Chat session",
            status=AnalysisRunStatus.COMPLETED,
            completed_at=datetime.now(UTC),
            graph_version=self._settings.graph_version,
        )
        self._session.add(session)
        await self._session.flush()
        return session

    async def send_chat_message(
        self,
        org_id: UUID,
        session_id: UUID,
        data: ChatMessageCreate,
    ) -> AnalysisRun:
        await self.get_run(org_id, session_id)

        run = AnalysisRun(
            org_id=org_id,
            creator_id=(await self.get_run(org_id, session_id)).creator_id,
            run_type=RunType.CHAT,
            query=data.message,
            filters={
                "session_id": str(session_id),
                **(data.filters.model_dump() if data.filters else {}),
            },
            status=AnalysisRunStatus.QUEUED,
            graph_version=self._settings.graph_version,
        )
        self._session.add(run)
        await self._session.flush()

        asyncio.create_task(
            self._run_chat_background(
                run_id=run.id,
                session_id=session_id,
                org_id=org_id,
                creator_id=run.creator_id,
                message=data.message,
                filters=run.filters,
            )
        )
        return run

    async def _run_chat_background(
        self,
        *,
        run_id: UUID,
        session_id: UUID,
        org_id: UUID,
        creator_id: UUID,
        message: str,
        filters: dict | None,
    ) -> None:
        async with async_session_factory() as session:
            runner = GraphRunnerService(session)
            try:
                await runner.run_chat(
                    run_id=run_id,
                    session_id=session_id,
                    org_id=org_id,
                    creator_id=creator_id,
                    user_query=message,
                    filters=filters,
                )
                await session.commit()
            except Exception:
                await session.rollback()

    async def stream_events(
        self,
        org_id: UUID,
        run_id: UUID,
        *,
        last_event_id: str | None,
    ) -> AsyncIterator[StreamEvent]:
        await self.get_run(org_id, run_id)
        await self._redis.connect()

        cursor = last_event_id or "0"
        idle_ticks = 0
        while idle_ticks < 6:
            events = await self._redis.read_stream(
                run_id,
                last_id=cursor,
                block_ms=3000,
                count=50,
            )
            if not events:
                idle_ticks += 1
                run = await self.get_run(org_id, run_id)
                if run.status in {AnalysisRunStatus.COMPLETED, AnalysisRunStatus.FAILED}:
                    break
                continue

            idle_ticks = 0
            for message_id, fields in events:
                cursor = message_id
                payload_raw = fields.get("payload", "{}")
                payload = json.loads(payload_raw)
                event_name = payload.pop("event", "status")
                try:
                    event_type = StreamEventType(event_name)
                except ValueError:
                    event_type = StreamEventType.STATUS
                yield StreamEvent(event=event_type, data=payload)

            run = await self.get_run(org_id, run_id)
            if run.status in {AnalysisRunStatus.COMPLETED, AnalysisRunStatus.FAILED}:
                break
