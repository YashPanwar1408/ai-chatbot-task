"""Content item ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import ContentType, Platform, ProcessingStatus

if TYPE_CHECKING:
    from app.db.models.chunk import Chunk
    from app.db.models.creator import Creator
    from app.db.models.transcript import Transcript


class ContentItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "content_items"
    __table_args__ = (
        UniqueConstraint(
            "creator_id",
            "platform",
            "platform_content_id",
            name="uq_content_items_creator_platform_content",
        ),
    )

    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creators.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, name="platform", native_enum=False),
        nullable=False,
    )
    platform_content_id: Mapped[str] = mapped_column(String(128), nullable=False)
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="content_type", native_enum=False),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    engagement: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status", native_enum=False),
        default=ProcessingStatus.PENDING,
        nullable=False,
    )
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    creator: Mapped[Creator] = relationship(back_populates="content_items")
    transcripts: Mapped[list[Transcript]] = relationship(back_populates="content_item")
    chunks: Mapped[list[Chunk]] = relationship(back_populates="content_item")
