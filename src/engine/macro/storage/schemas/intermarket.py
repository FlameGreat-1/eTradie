from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class IntermarketSnapshotRow(Base):
    __tablename__ = "intermarket_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gold_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    silver_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    oil_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    us2y_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    us10y_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    us30y_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    dxy_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    sp500: Mapped[float | None] = mapped_column(Float, nullable=True)
    vix: Mapped[float | None] = mapped_column(Float, nullable=True)
    correlation_signals_json: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_intermarket_snapshot_at", "snapshot_at"),
    )
