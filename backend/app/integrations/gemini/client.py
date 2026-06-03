"""Google Gemini LLM client wrapper."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config.settings import Settings, get_settings
from app.domain.exceptions import IntegrationError

logger = logging.getLogger(__name__)

_RETRYABLE_PATTERN = re.compile(
    r"(429|503|resource_exhausted|unavailable|quota|rate.?limit|high demand)",
    re.IGNORECASE,
)


def _friendly_gemini_error(exc: Exception) -> str:
    text = str(exc)
    if "429" in text or "RESOURCE_EXHAUSTED" in text or "quota" in text.lower():
        return (
            "Gemini API rate limit reached (free tier allows few requests per minute). "
            "Wait 1–2 minutes and try again, set GEMINI_MODEL=gemini-2.0-flash, "
            "or disable GEMINI_LLM_GRADING. See https://ai.google.dev/gemini-api/docs/rate-limits"
        )
    if "503" in text or "UNAVAILABLE" in text:
        return (
            "Gemini model is temporarily overloaded. Retry in a few seconds or set "
            "GEMINI_MODEL=gemini-2.0-flash in .env"
        )
    if "API_KEY_INVALID" in text or "401" in text or "403" in text:
        return (
            "Invalid GOOGLE_API_KEY. Create a key at https://aistudio.google.com/apikey "
            "(must start with AIzaSy, not AQ.)"
        )
    return text[:500]


class GeminiClient:
    """Wrapper for Gemini invocations with retries on transient errors."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self.model_name = self._settings.gemini_model
        key = self._settings.google_api_key
        if key and not key.startswith("AIza"):
            logger.warning(
                "GOOGLE_API_KEY should start with AIzaSy from "
                "https://aistudio.google.com/apikey (got unexpected prefix)"
            )
        if not key:
            self._llm = None
        else:
            self._llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=key,
                temperature=0.2,
            )

    def _require_llm(self) -> ChatGoogleGenerativeAI:
        if self._llm is None:
            raise IntegrationError("gemini", "GOOGLE_API_KEY is not configured")
        return self._llm

    async def _invoke_with_retry(self, llm: ChatGoogleGenerativeAI, messages: list) -> str:
        last_exc: Exception | None = None
        delays = (1.0, 2.0, 4.0, 8.0, 16.0)
        for attempt, delay in enumerate(delays, start=1):
            try:
                response = await llm.ainvoke(messages)
                content = response.content
                return content if isinstance(content, str) else str(content)
            except Exception as exc:
                last_exc = exc
                if not _RETRYABLE_PATTERN.search(str(exc)) or attempt == len(delays):
                    raise IntegrationError("gemini", _friendly_gemini_error(exc)) from exc
                logger.info("Gemini retry %s/%s after %ss", attempt, len(delays), delay)
                await asyncio.sleep(delay)
        raise IntegrationError("gemini", _friendly_gemini_error(last_exc or Exception("unknown")))

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        llm = self._require_llm()
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))
        return await self._invoke_with_retry(llm, messages)

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

        last_exc: Exception | None = None
        delays = (1.0, 2.0, 4.0)
        for attempt, delay in enumerate(delays, start=1):
            try:
                async for chunk in llm.astream(messages):
                    content = chunk.content
                    if isinstance(content, str) and content:
                        yield content
                return
            except Exception as exc:
                last_exc = exc
                if not _RETRYABLE_PATTERN.search(str(exc)) or attempt == len(delays):
                    raise IntegrationError("gemini", _friendly_gemini_error(exc)) from exc
                logger.info("Gemini stream retry %s/%s", attempt, len(delays))
                await asyncio.sleep(delay)
        raise IntegrationError("gemini", _friendly_gemini_error(last_exc or Exception("unknown")))

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
