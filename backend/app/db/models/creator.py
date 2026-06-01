"""Creator ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import IngestStatus

if TYPE_CHECKING:
    from app.db.models.content_item import ContentItem
    from app.db.models.organization import Organization


class Creator(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "creators"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    youtube_channel_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    instagram_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ingest_status: Mapped[IngestStatus] = mapped_column(
        Enum(IngestStatus, name="ingest_status", native_enum=False),
        default=IngestStatus.IDLE,
        nullable=False,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="creators")
    content_items: Mapped[list[ContentItem]] = relationship(back_populates="creator")
