from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class CandleSchema(Base):
    """
    Database schema for candle storage.

    Stores OHLCV data with:
    - User-scoped ownership (every row belongs to a specific user)
    - Immutable historical records (never modified after insert)
    - Symbol/timeframe/timestamp composite index for fast queries
    - Support for backfill and real-time updates

    Indexes:
    - (user_id, symbol, timeframe, timestamp) - primary query pattern (unique)
    - user_id - per-user filtering
    - timestamp - time-based filtering
    """

    __tablename__ = "candles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    user_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    timeframe: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    open: Mapped[float] = mapped_column(Float, nullable=False)

    high: Mapped[float] = mapped_column(Float, nullable=False)

    low: Mapped[float] = mapped_column(Float, nullable=False)

    close: Mapped[float] = mapped_column(Float, nullable=False)

    volume: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Derived timestamps — populated by the repository from timestamp
    # + timeframe duration. Nullable because the Candle domain model
    # does not carry these; they are storage-layer concerns only.
    open_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    close_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Optional exchange metadata — nullable because MT5/TwelveData
    # do not provide these fields. Only relevant for crypto exchanges.
    quote_volume: Mapped[float] = mapped_column(Float, nullable=True)

    number_of_trades: Mapped[int] = mapped_column(Integer, nullable=True)

    taker_buy_base_volume: Mapped[float] = mapped_column(
        Float,
        nullable=True,
    )

    taker_buy_quote_volume: Mapped[float] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index(
            "ix_candles_user_symbol_timeframe_timestamp",
            "user_id",
            "symbol",
            "timeframe",
            "timestamp",
            unique=True,
        ),
    )
