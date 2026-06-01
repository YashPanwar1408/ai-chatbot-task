"""Redis client for caching, rate limits, SSE streams, and chat memory."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any
from uuid import UUID

import redis.asyncio as redis

from app.config.settings import Settings, get_settings
from app.domain.exceptions import IntegrationError


class RedisClient:
    """Async Redis wrapper."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._redis: redis.Redis | None = None

    async def connect(self) -> None:
        if self._redis is None:
            self._redis = redis.from_url(
                self._settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

    @property
    def client(self) -> redis.Redis:
        if self._redis is None:
            raise IntegrationError("redis", "Client not connected; call connect() first")
        return self._redis

    def stream_key(self, run_id: UUID) -> str:
        return f"{self._settings.redis_stream_prefix}:{run_id}"

    def chat_memory_key(self, session_id: UUID) -> str:
        return f"chat:memory:{session_id}"

    async def publish_stream_event(self, run_id: UUID, event: str, data: dict[str, Any]) -> str:
        await self.connect()
        payload = {"event": event, **data}
        message_id = await self.client.xadd(
            self.stream_key(run_id),
            {"payload": json.dumps(payload)},
        )
        return str(message_id)

    async def read_stream(
        self,
        run_id: UUID,
        *,
        last_id: str = "0",
        block_ms: int = 5000,
        count: int = 20,
    ) -> list[tuple[str, dict[str, str]]]:
        await self.connect()
        start_id = last_id if last_id != "0" else "0-0"
        result = await self.client.xread(
            {self.stream_key(run_id): start_id},
            count=count,
            block=block_ms,
        )
        events: list[tuple[str, dict[str, str]]] = []
        for _stream, messages in result:
            for message_id, fields in messages:
                events.append((message_id, fields))
        return events

    async def cache_get(self, key: str) -> str | None:
        await self.connect()
        return await self.client.get(key)

    async def cache_set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self.connect()
        await self.client.set(key, value, ex=ttl_seconds)

    async def get_chat_memory(self, session_id: UUID) -> list[dict[str, str]]:
        await self.connect()
        raw = await self.client.get(self.chat_memory_key(session_id))
        if not raw:
            return []
        return json.loads(raw)

    async def append_chat_memory(
        self,
        session_id: UUID,
        role: str,
        content: str,
    ) -> list[dict[str, str]]:
        await self.connect()
        messages = await self.get_chat_memory(session_id)
        messages.append({"role": role, "content": content})
        max_messages = self._settings.chat_memory_max_messages
        if len(messages) > max_messages:
            messages = messages[-max_messages:]
        await self.client.set(
            self.chat_memory_key(session_id),
            json.dumps(messages),
            ex=self._settings.chat_memory_ttl_seconds,
        )
        return messages

    async def health_check(self) -> bool:
        await self.connect()
        try:
            return bool(await self.client.ping())
        except Exception as exc:
            raise IntegrationError("redis", str(exc)) from exc

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


@lru_cache
def get_redis_client() -> RedisClient:
    return RedisClient()
