from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class SentimentReadingRow(Base):
    __tablename__ = "sentiment_readings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(5), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    long_percentage: Mapped[float] = mapped_column(
        Float, nullable=False, default=50.0
    )
    short_percentage: Mapped[float] = mapped_column(
        Float, nullable=False, default=50.0
    )
    net_positioning: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "currency", "source",
            name="uq_sentiment_user_currency_source",
        ),
        Index("ix_sentiment_user_id", "user_id"),
        Index("ix_sentiment_user_currency", "user_id", "currency"),
        Index("ix_sentiment_user_collected_at", "user_id", "collected_at"),
    )
