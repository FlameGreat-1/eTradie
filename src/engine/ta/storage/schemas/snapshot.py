from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Index, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from engine.shared.database.base import Base


class SnapshotSchema(Base):
    """
    Database schema for TechnicalSnapshot storage.
    
    Stores complete technical analysis snapshots with:
    - All detected primitives (swings, structure events, zones, liquidity)
    - Versioning support (track changes over time)
    - Symbol/timeframe/timestamp indexing
    - JSON metadata for flexible storage
    
    Snapshots are immutable once created.
    New analysis creates new snapshot version.
    
    Indexes:
    - (symbol, timeframe, timestamp) - primary query pattern
    - (symbol, timeframe, created_at) - version tracking
    - timestamp - time-based filtering
    """
    
    __tablename__ = "technical_snapshots"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    swing_highs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    swing_lows: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    bms_events: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    choch_events: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    sms_events: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    order_blocks: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    fair_value_gaps: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    liquidity_sweeps: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    inducement_events: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    qm_levels: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    sr_flips: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    rs_flips: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    previous_levels: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    mpl_levels: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    fakeout_tests: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    supply_zones: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    demand_zones: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    fibonacci_retracements: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    metadata: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    
    __table_args__ = (
        Index(
            "ix_snapshots_symbol_timeframe_timestamp",
            "symbol",
            "timeframe",
            "timestamp",
        ),
        Index(
            "ix_snapshots_symbol_timeframe_created_at",
            "symbol",
            "timeframe",
            "created_at",
        ),
    )
