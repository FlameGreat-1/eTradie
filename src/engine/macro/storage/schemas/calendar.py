from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class CalendarEventRow(Base):
    __tablename__ = "calendar_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_name: Mapped[str] = mapped_column(String(300), nullable=False)
    currency: Mapped[str] = mapped_column(String(5), nullable=False)
    impact: Mapped[str] = mapped_column(String(10), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    forecast: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    previous: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_cal_currency_time", "currency", "event_time"),
        Index("ix_cal_event_time", "event_time"),
        Index("ix_cal_impact_time", "impact", "event_time"),
    )
