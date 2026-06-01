"""Google Gemini LLM client wrapper."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config.settings import Settings, get_settings
from app.domain.exceptions import IntegrationError


class GeminiClient:
    """Wrapper for Gemini 2.5 Flash invocations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self.model_name = self._settings.gemini_model
        if not self._settings.google_api_key:
            self._llm = None
        else:
            self._llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self._settings.google_api_key,
                temperature=0.2,
            )

    def _require_llm(self) -> ChatGoogleGenerativeAI:
        if self._llm is None:
            raise IntegrationError("gemini", "GOOGLE_API_KEY is not configured")
        return self._llm

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        llm = self._require_llm()
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))
        response = await llm.ainvoke(messages)
        content = response.content
        return content if isinstance(content, str) else str(content)

    async def generate_stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
    ) -> AsyncIterator[str]:
        llm = self._require_llm()
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))
        async for chunk in llm.astream(messages):
            content = chunk.content
            if isinstance(content, str) and content:
                yield content

    async def grade_relevance(self, query: str, chunk_text: str) -> bool:
        prompt = (
            "You are a retrieval grader. Reply with only YES or NO.\n"
            f"Question: {query}\n"
            f"Document: {chunk_text[:1200]}"
        )
        result = (await self.generate(prompt)).strip().upper()
        return result.startswith("YES")


@lru_cache
def get_gemini_client() -> GeminiClient:
    return GeminiClient()
