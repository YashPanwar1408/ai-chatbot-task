"""Domain-layer types (non-Pydantic, non-ORM)."""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class PaginatedResult(Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    total: int | None = None
