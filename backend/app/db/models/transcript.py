"""Transcript ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import TranscriptSource

if TYPE_CHECKING:
    from app.db.models.chunk import Chunk
    from app.db.models.content_item import ContentItem


class Transcript(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "transcripts"

    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[TranscriptSource] = mapped_column(
        Enum(TranscriptSource, name="transcript_source", native_enum=False),
        nullable=False,
    )
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    segments: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    content_item: Mapped[ContentItem] = relationship(back_populates="transcripts")
    chunks: Mapped[list[Chunk]] = relationship(back_populates="transcript")
