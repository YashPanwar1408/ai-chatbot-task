"""In-process Redis substitute for SSE streams and chat memory (local dev)."""

from __future__ import annotations

import json
import itertools
from typing import Any
from uuid import UUID

from app.config.settings import Settings, get_settings


class InMemoryRedisStore:
    _counter = itertools.count(1)

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._kv: dict[str, str] = {}

    def stream_key(self, run_id: UUID) -> str:
        return f"{self._settings.redis_stream_prefix}:{run_id}"

    def chat_memory_key(self, session_id: UUID) -> str:
        return f"chat:memory:{session_id}"

    async def connect(self) -> None:
        return None

    async def ping(self) -> bool:
        return True

    async def publish_stream_event(self, run_id: UUID, event: str, data: dict[str, Any]) -> str:
        key = self.stream_key(run_id)
        message_id = f"{next(self._counter)}-0"
        payload = {"event": event, **data}
        self._streams.setdefault(key, []).append(
            (message_id, {"payload": json.dumps(payload)}),
        )
        return message_id

    async def read_stream(
        self,
        run_id: UUID,
        *,
        last_id: str = "0",
        block_ms: int = 5000,
        count: int = 20,
    ) -> list[tuple[str, dict[str, str]]]:
        _ = block_ms
        key = self.stream_key(run_id)
        messages = self._streams.get(key, [])
        if last_id in ("0", "0-0"):
            start_index = 0
        else:
            start_index = 0
            for index, (message_id, _) in enumerate(messages):
                if message_id == last_id:
                    start_index = index + 1
                    break
        return messages[start_index : start_index + count]

    async def get(self, key: str) -> str | None:
        return self._kv.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        _ = ex
        self._kv[key] = value

    async def aclose(self) -> None:
        return None
