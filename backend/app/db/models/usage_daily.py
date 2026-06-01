"""Daily usage quota ORM model."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsageDaily(Base):
    __tablename__ = "usage_daily"
    __table_args__ = (PrimaryKeyConstraint("org_id", "date", name="pk_usage_daily"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    creators_synced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    videos_ingested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embed_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    llm_input_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    llm_output_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
