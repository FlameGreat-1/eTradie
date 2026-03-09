from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, Float, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.db.migrations._schema_registry import Base


class CandleSchema(Base):
    """
    Database schema for candle storage.
    
    Stores OHLCV data with:
    - Immutable historical records (never modified after insert)
    - Symbol/timeframe/timestamp composite index for fast queries
    - Support for backfill and real-time updates
    - Cache snapshots for quick retrieval
    
    Indexes:
    - (symbol, timeframe, timestamp) - primary query pattern
    - (symbol, timeframe, open_time) - chronological ordering
    - timestamp - time-based filtering
    """
    
    __tablename__ = "candles"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    open: Mapped[float] = mapped_column(Float, nullable=False)
    
    high: Mapped[float] = mapped_column(Float, nullable=False)
    
    low: Mapped[float] = mapped_column(Float, nullable=False)
    
    close: Mapped[float] = mapped_column(Float, nullable=False)
    
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    
    quote_volume: Mapped[float] = mapped_column(Float, nullable=True)
    
    number_of_trades: Mapped[int] = mapped_column(Integer, nullable=True)
    
    taker_buy_base_volume: Mapped[float] = mapped_column(Float, nullable=True)
    
    taker_buy_quote_volume: Mapped[float] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    
    __table_args__ = (
        Index(
            "ix_candles_symbol_timeframe_timestamp",
            "symbol",
            "timeframe",
            "timestamp",
            unique=True,
        ),
        Index(
            "ix_candles_symbol_timeframe_open_time",
            "symbol",
            "timeframe",
            "open_time",
        ),
    )
