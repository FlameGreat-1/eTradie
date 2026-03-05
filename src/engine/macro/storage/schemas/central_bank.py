from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class CentralBankEventRow(Base):
    __tablename__ = "central_bank_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank: Mapped[str] = mapped_column(String(10), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    speaker: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    tone: Mapped[str] = mapped_column(String(10), nullable=False, default="NEUTRAL")
    tone_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    rate_current: Mapped[float | None] = mapped_column(nullable=True)
    rate_previous: Mapped[float | None] = mapped_column(nullable=True)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_cb_events_bank_timestamp", "bank", "event_timestamp"),
        Index("ix_cb_events_event_type", "event_type"),
        Index("ix_cb_events_created_at", "created_at"),
    )
