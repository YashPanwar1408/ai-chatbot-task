"""Redis client with in-memory fallback for local dev without Docker."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any
from uuid import UUID

import redis.asyncio as redis

from app.config.settings import Settings, get_settings
from app.domain.exceptions import IntegrationError
from app.integrations.redis.memory_store import InMemoryRedisStore

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis wrapper with in-process fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._memory = InMemoryRedisStore(self._settings)
        self._redis: redis.Redis | None = None
        self._use_memory = self._settings.redis_use_memory

    @property
    def using_memory(self) -> bool:
        return self._use_memory

    async def _activate_memory_fallback(self, exc: Exception | None = None) -> None:
        if self._use_memory:
            return
        self._use_memory = True
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None
        reason = str(exc) if exc else "unavailable"
        logger.warning("Redis unavailable (%s); using in-memory streams/memory", reason)

    async def connect(self) -> None:
        if self._use_memory:
            await self._memory.connect()
            return
        if self._redis is None:
            self._redis = redis.from_url(
                self._settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        try:
            await self._redis.ping()
        except Exception as exc:
            await self._activate_memory_fallback(exc)
            await self._memory.connect()

    @property
    def client(self) -> redis.Redis:
        if self._use_memory or self._redis is None:
            raise IntegrationError("redis", "Remote Redis not active (memory fallback)")
        return self._redis

    def stream_key(self, run_id: UUID) -> str:
        return self._memory.stream_key(run_id)

    def chat_memory_key(self, session_id: UUID) -> str:
        return self._memory.chat_memory_key(session_id)

    async def publish_stream_event(self, run_id: UUID, event: str, data: dict[str, Any]) -> str:
        await self.connect()
        if self._use_memory:
            return await self._memory.publish_stream_event(run_id, event, data)
        try:
            payload = {"event": event, **data}
            message_id = await self.client.xadd(
                self.stream_key(run_id),
                {"payload": json.dumps(payload)},
            )
            return str(message_id)
        except Exception as exc:
            await self._activate_memory_fallback(exc)
            return await self._memory.publish_stream_event(run_id, event, data)

    async def read_stream(
        self,
        run_id: UUID,
        *,
        last_id: str = "0",
        block_ms: int = 5000,
        count: int = 20,
    ) -> list[tuple[str, dict[str, str]]]:
        await self.connect()
        if self._use_memory:
            return await self._memory.read_stream(
                run_id,
                last_id=last_id,
                block_ms=block_ms,
                count=count,
            )
        start_id = last_id if last_id != "0" else "0-0"
        try:
            result = await self.client.xread(
                {self.stream_key(run_id): start_id},
                count=count,
                block=block_ms,
            )
        except Exception as exc:
            await self._activate_memory_fallback(exc)
            return await self._memory.read_stream(
                run_id,
                last_id=last_id,
                block_ms=0,
                count=count,
            )
        events: list[tuple[str, dict[str, str]]] = []
        for _stream, messages in result:
            for message_id, fields in messages:
                events.append((message_id, fields))
        return events

    async def cache_get(self, key: str) -> str | None:
        await self.connect()
        if self._use_memory:
            return await self._memory.get(key)
        return await self.client.get(key)

    async def cache_set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self.connect()
        if self._use_memory:
            await self._memory.set(key, value, ex=ttl_seconds)
            return
        await self.client.set(key, value, ex=ttl_seconds)

    async def get_chat_memory(self, session_id: UUID) -> list[dict[str, str]]:
        await self.connect()
        key = self.chat_memory_key(session_id)
        if self._use_memory:
            raw = await self._memory.get(key)
        else:
            raw = await self.client.get(key)
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
        key = self.chat_memory_key(session_id)
        payload = json.dumps(messages)
        if self._use_memory:
            await self._memory.set(key, payload, ex=self._settings.chat_memory_ttl_seconds)
        else:
            await self.client.set(
                key,
                payload,
                ex=self._settings.chat_memory_ttl_seconds,
            )
        return messages

    async def health_check(self) -> bool:
        await self.connect()
        if self._use_memory:
            return True
        try:
            return bool(await self.client.ping())
        except Exception as exc:
            raise IntegrationError("redis", str(exc)) from exc

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
        await self._memory.aclose()


@lru_cache
def get_redis_client() -> RedisClient:
    return RedisClient()
