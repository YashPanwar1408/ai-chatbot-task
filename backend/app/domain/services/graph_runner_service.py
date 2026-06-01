"""Execute LangGraph workflows and publish streaming events."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.enums import AnalysisRunStatus
from app.db.models.analysis_run import AnalysisRun
from app.db.models.citation import Citation
from app.graph.graphs.chat_graph import build_chat_graph
from app.graph.state import ChatGraphState
from app.integrations.redis.client import get_redis_client


class GraphRunnerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()
        self._redis = get_redis_client()
        self._chat_graph = build_chat_graph()

    async def run_chat(
        self,
        *,
        run_id: UUID,
        session_id: UUID,
        org_id: UUID,
        creator_id: UUID,
        user_query: str,
        filters: dict | None = None,
    ) -> AnalysisRun:
        run = await self._get_run(run_id, org_id)
        run.status = AnalysisRunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        await self._session.flush()

        initial_state: ChatGraphState = {
            "run_id": str(run_id),
            "session_id": str(session_id),
            "org_id": str(org_id),
            "creator_id": str(creator_id),
            "user_query": user_query,
            "filters": filters or {},
            "retrieval_attempts": 0,
        }

        try:
            final_state = await self._chat_graph.ainvoke(initial_state)
            run.status = AnalysisRunStatus.COMPLETED
            run.completed_at = datetime.now(UTC)
            run.result_summary = {
                "answer": final_state.get("draft_answer", ""),
                "citations": final_state.get("citations", []),
            }
            await self._persist_citations(run.id, final_state.get("citations", []))
            await self._redis.publish_stream_event(
                run_id,
                "done",
                {"run_id": str(run_id), "status": run.status.value},
            )
        except Exception as exc:
            run.status = AnalysisRunStatus.FAILED
            run.error = str(exc)
            run.completed_at = datetime.now(UTC)
            await self._redis.publish_stream_event(
                run_id,
                "error",
                {"message": str(exc)},
            )
            raise
        finally:
            await self._session.flush()

        return run

    async def _get_run(self, run_id: UUID, org_id: UUID) -> AnalysisRun:
        result = await self._session.execute(
            select(AnalysisRun).where(AnalysisRun.id == run_id, AnalysisRun.org_id == org_id)
        )
        run = result.scalar_one_or_none()
        if run is None:
            from app.domain.exceptions import NotFoundError

            raise NotFoundError("analysis_run", str(run_id))
        return run

    async def _persist_citations(self, run_id: UUID, citations: list[dict]) -> None:
        for citation in citations:
            chunk_id = citation.get("chunk_id")
            content_item_id = citation.get("content_item_id")
            if not chunk_id or not content_item_id:
                continue
            self._session.add(
                Citation(
                    analysis_run_id=run_id,
                    chunk_id=UUID(str(chunk_id)),
                    content_item_id=UUID(str(content_item_id)),
                    score=citation.get("score"),
                    rank=citation.get("rank"),
                )
            )
        await self._session.flush()
