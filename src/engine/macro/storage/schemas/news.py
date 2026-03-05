from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class NewsItemRow(Base):
    __tablename__ = "news_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    headline: Mapped[str] = mapped_column(String(1000), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    currencies: Mapped[list[str]] = mapped_column(ARRAY(String(5)), nullable=False, default=[])
    sentiment: Mapped[str] = mapped_column(String(15), nullable=False, default="NEUTRAL")
    impact: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIUM")
    dedupe_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("dedupe_hash", name="uq_news_dedupe_hash"),
        Index("ix_news_published_at", "published_at"),
        Index("ix_news_impact", "impact"),
    )
