from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class EconomicReleaseRow(Base):
    __tablename__ = "economic_releases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    currency: Mapped[str] = mapped_column(String(5), nullable=False)
    indicator: Mapped[str] = mapped_column(String(30), nullable=False)
    indicator_name: Mapped[str] = mapped_column(String(200), nullable=False)
    actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous: Mapped[float | None] = mapped_column(Float, nullable=True)
    surprise: Mapped[float | None] = mapped_column(Float, nullable=True)
    surprise_direction: Mapped[str] = mapped_column(String(10), nullable=False, default="INLINE")
    impact: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIUM")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    release_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_econ_currency_indicator", "currency", "indicator"),
        Index("ix_econ_release_time", "release_time"),
        Index("ix_econ_currency_release", "currency", "release_time"),
    )
