"""Shared schema primitives."""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TimestampSchema(SchemaBase):
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(SchemaBase, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    total: int | None = None


class MessageResponse(SchemaBase):
    message: str


class ErrorResponse(SchemaBase):
    detail: str
    code: str | None = None


class HealthResponse(SchemaBase):
    status: str


class ReadyResponse(SchemaBase):
    status: str
    postgres: bool
    redis: bool
    qdrant: bool


class IdResponse(SchemaBase):
    id: UUID
