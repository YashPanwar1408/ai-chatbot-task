"""Compare and URL-ingest domain service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.enums import AnalysisRunStatus, IngestStatus, Platform, RunType
from app.db.models.analysis_run import AnalysisRun
from app.db.models.creator import Creator
from app.domain.exceptions import NotFoundError
from app.domain.services.video_ingest_service import VideoIngestService
from app.graph.graphs.chat_graph import build_chat_graph
from app.graph.state import ChatGraphState
from app.schemas.compare import CompareCreateRequest, CompareUrlsRequest


class CompareService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()
        self._ingest = VideoIngestService(session)
        self._chat_graph = build_chat_graph()

    async def ingest_urls(
        self,
        org_id: UUID,
        request: CompareUrlsRequest,
    ) -> dict:
        creator = await self._ingest.create_comparison_creator(
            org_id,
            display_name=request.display_name or "YouTube vs Instagram Comparison",
        )

        youtube_item, youtube_extract = await self._ingest.ingest_from_url(
            org_id=org_id,
            creator_id=creator.id,
            url=request.youtube_url,
            platform=Platform.YOUTUBE,
        )
        instagram_item, instagram_extract = await self._ingest.ingest_from_url(
            org_id=org_id,
            creator_id=creator.id,
            url=request.instagram_url,
            platform=Platform.INSTAGRAM,
        )

        creator.ingest_status = IngestStatus.READY
        creator.last_synced_at = datetime.now(UTC)
        creator.metadata_ = {
            "youtube_content_id": str(youtube_item.id),
            "instagram_content_id": str(instagram_item.id),
        }
        await self._session.flush()

        response = {
            "creator_id": creator.id,
            "youtube": {
                "content_id": youtube_item.id,
                **VideoIngestService.engagement_summary(youtube_extract),
                "transcript_preview": youtube_extract.transcript[:500],
            },
            "instagram": {
                "content_id": instagram_item.id,
                **VideoIngestService.engagement_summary(instagram_extract),
                "transcript_preview": instagram_extract.transcript[:500],
            },
        }

        if request.query:
            run = await self.start_compare(
                org_id,
                CompareCreateRequest(
                    creator_id=creator.id,
                    query=request.query,
                    filters=request.filters,
                ),
            )
            response["run_id"] = run.id
            response["run_status"] = run.status

        return response

    async def start_compare(self, org_id: UUID, request: CompareCreateRequest) -> AnalysisRun:
        creator = await self._get_creator(org_id, request.creator_id)
        query = request.query or self._default_compare_query()

        run = AnalysisRun(
            org_id=org_id,
            creator_id=creator.id,
            run_type=RunType.COMPARE,
            query=query,
            filters=request.filters.model_dump() if request.filters else None,
            status=AnalysisRunStatus.RUNNING,
            graph_version=self._settings.graph_version,
            started_at=datetime.now(UTC),
        )
        self._session.add(run)
        await self._session.flush()

        initial_state: ChatGraphState = {
            "run_id": str(run.id),
            "session_id": str(run.id),
            "org_id": str(org_id),
            "creator_id": str(creator.id),
            "user_query": query,
            "filters": request.filters.model_dump() if request.filters else {},
            "retrieval_attempts": 0,
        }
        final_state = await self._chat_graph.ainvoke(initial_state)
        run.status = AnalysisRunStatus.COMPLETED
        run.completed_at = datetime.now(UTC)
        run.result_summary = {
            "answer": final_state.get("draft_answer", ""),
            "citations": final_state.get("citations", []),
        }
        await self._session.flush()
        return run

    async def get_result(self, org_id: UUID, run_id: UUID) -> AnalysisRun:
        result = await self._session.execute(
            select(AnalysisRun).where(AnalysisRun.id == run_id, AnalysisRun.org_id == org_id)
        )
        run = result.scalar_one_or_none()
        if run is None:
            raise NotFoundError("analysis_run", str(run_id))
        return run

    async def _get_creator(self, org_id: UUID, creator_id: UUID) -> Creator:
        result = await self._session.execute(
            select(Creator).where(Creator.id == creator_id, Creator.org_id == org_id)
        )
        creator = result.scalar_one_or_none()
        if creator is None:
            raise NotFoundError("creator", str(creator_id))
        return creator

    @staticmethod
    def _default_compare_query() -> str:
        return (
            "Compare the YouTube Short and Instagram Reel across hook, topic, pacing, "
            "hashtags, and engagement efficiency. Cite evidence from both videos."
        )
