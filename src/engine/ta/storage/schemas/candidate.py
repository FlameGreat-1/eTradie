from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, Float, DateTime, Index, JSON, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.database.base import Base


class CandidateSchema(Base):
    """
    Database schema for SMC/SnD candidate storage.
    
    Stores deterministic candidate outputs with:
    - Complete pattern information (SMC or SnD)
    - Entry/SL/TP levels
    - All confluences and validations
    - Deduplication (same pattern not stored twice)
    - Symbol/timeframe/timestamp indexing
    
    Candidates are immutable once created.
    Each candidate represents a unique trading opportunity.
    
    Indexes:
    - (symbol, timeframe, timestamp) - primary query pattern
    - (symbol, pattern, direction) - pattern-based filtering
    - (is_active, timestamp) - active candidate queries
    - timestamp - time-based filtering
    """
    
    __tablename__ = "candidates"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    pattern: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    direction: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    
    stop_loss: Mapped[float] = mapped_column(Float, nullable=False)
    
    take_profit: Mapped[float] = mapped_column(Float, nullable=False)
    
    htf_timeframe: Mapped[str] = mapped_column(String(10), nullable=True)
    
    ltf_timeframe: Mapped[str] = mapped_column(String(10), nullable=True)
    
    is_smc: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    is_snd: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    sms_detected: Mapped[bool] = mapped_column(Boolean, nullable=True)
    
    sms_price: Mapped[float] = mapped_column(Float, nullable=True)
    
    sms_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    bms_detected: Mapped[bool] = mapped_column(Boolean, nullable=True)
    
    bms_price: Mapped[float] = mapped_column(Float, nullable=True)
    
    bms_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    choch_detected: Mapped[bool] = mapped_column(Boolean, nullable=True)
    
    choch_price: Mapped[float] = mapped_column(Float, nullable=True)
    
    choch_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    order_block_upper: Mapped[float] = mapped_column(Float, nullable=True)
    
    order_block_lower: Mapped[float] = mapped_column(Float, nullable=True)
    
    order_block_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    liquidity_swept: Mapped[bool] = mapped_column(Boolean, nullable=True)
    
    swept_level: Mapped[float] = mapped_column(Float, nullable=True)
    
    sweep_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    inducement_cleared: Mapped[bool] = mapped_column(Boolean, nullable=True)
    
    ltf_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=True)
    
    ltf_confirmation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    displacement_pips: Mapped[float] = mapped_column(Float, nullable=True)
    
    fib_level: Mapped[str] = mapped_column(String(20), nullable=True)
    
    session_context: Mapped[str] = mapped_column(String(50), nullable=True)
    
    qml_level: Mapped[float] = mapped_column(Float, nullable=True)
    
    qml_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    qmh_level: Mapped[float] = mapped_column(Float, nullable=True)
    
    qmh_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    sr_flip_level: Mapped[float] = mapped_column(Float, nullable=True)
    
    rs_flip_level: Mapped[float] = mapped_column(Float, nullable=True)
    
    fakeout_count: Mapped[int] = mapped_column(nullable=True)
    
    has_compression: Mapped[bool] = mapped_column(Boolean, nullable=True)
    
    has_previous_highs: Mapped[bool] = mapped_column(Boolean, nullable=True)
    
    previous_highs_count: Mapped[int] = mapped_column(nullable=True)
    
    has_previous_lows: Mapped[bool] = mapped_column(Boolean, nullable=True)
    
    previous_lows_count: Mapped[int] = mapped_column(nullable=True)
    
    has_mpl: Mapped[bool] = mapped_column(Boolean, nullable=True)
    
    mpl_level: Mapped[float] = mapped_column(Float, nullable=True)
    
    metadata: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    
    invalidated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    invalidation_reason: Mapped[str] = mapped_column(Text, nullable=True)
    
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    
    __table_args__ = (
        Index(
            "ix_candidates_symbol_timeframe_timestamp",
            "symbol",
            "timeframe",
            "timestamp",
        ),
        Index(
            "ix_candidates_symbol_pattern_direction",
            "symbol",
            "pattern",
            "direction",
        ),
        Index(
            "ix_candidates_is_active_timestamp",
            "is_active",
            "timestamp",
        ),
    )
