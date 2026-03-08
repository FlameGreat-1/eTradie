from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from engine.shared.logging import get_logger
from engine.ta.storage.schemas.snapshot import SnapshotSchema

logger = get_logger(__name__)


class SnapshotRepository:
    """
    Repository for TechnicalSnapshot aggregate persistence and versioning.
    
    Provides:
    - Snapshot storage (immutable once created)
    - Version tracking (new analysis = new version)
    - Symbol/timeframe/timestamp queries
    - Latest snapshot retrieval
    - Historical snapshot access
    
    All operations are async for non-blocking I/O.
    """
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._logger = get_logger(__name__)
    
    async def create(
        self,
        symbol: str,
        timeframe: str,
        timestamp: datetime,
        swing_highs: dict,
        swing_lows: dict,
        bms_events: dict,
        choch_events: dict,
        sms_events: dict,
        order_blocks: dict,
        fair_value_gaps: dict,
        liquidity_sweeps: dict,
        inducement_events: dict,
        qm_levels: dict,
        sr_flips: dict,
        rs_flips: dict,
        previous_levels: dict,
        mpl_levels: dict,
        fakeout_tests: dict,
        supply_zones: dict,
        demand_zones: dict,
        fibonacci_retracements: dict,
        metadata: Optional[dict] = None,
        notes: Optional[str] = None,
    ) -> SnapshotSchema:
        """Create a new technical snapshot."""
        latest_version = await self._get_latest_version(symbol, timeframe)
        
        schema = SnapshotSchema(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            bms_events=bms_events,
            choch_events=choch_events,
            sms_events=sms_events,
            order_blocks=order_blocks,
            fair_value_gaps=fair_value_gaps,
            liquidity_sweeps=liquidity_sweeps,
            inducement_events=inducement_events,
            qm_levels=qm_levels,
            sr_flips=sr_flips,
            rs_flips=rs_flips,
            previous_levels=previous_levels,
            mpl_levels=mpl_levels,
            fakeout_tests=fakeout_tests,
            supply_zones=supply_zones,
            demand_zones=demand_zones,
            fibonacci_retracements=fibonacci_retracements,
            metadata=metadata,
            version=latest_version + 1,
            notes=notes,
        )
        
        self.session.add(schema)
        await self.session.flush()
        
        self._logger.debug(
            "snapshot_created",
            extra={
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": timestamp.isoformat(),
                "version": schema.version,
            },
        )
        
        return schema
    
    async def get_by_id(self, snapshot_id: UUID) -> Optional[SnapshotSchema]:
        """Retrieve snapshot by ID."""
        result = await self.session.execute(
            select(SnapshotSchema).where(SnapshotSchema.id == snapshot_id)
        )
        return result.scalar_one_or_none()
    
    async def find_by_symbol_timeframe_timestamp(
        self,
        symbol: str,
        timeframe: str,
        timestamp: datetime,
    ) -> Optional[SnapshotSchema]:
        """Find snapshot by symbol, timeframe, and timestamp."""
        result = await self.session.execute(
            select(SnapshotSchema)
            .where(
                and_(
                    SnapshotSchema.symbol == symbol,
                    SnapshotSchema.timeframe == timeframe,
                    SnapshotSchema.timestamp == timestamp,
                )
            )
            .order_by(desc(SnapshotSchema.version))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_latest_snapshot(
        self,
        symbol: str,
        timeframe: str,
    ) -> Optional[SnapshotSchema]:
        """Get most recent snapshot for symbol/timeframe."""
        result = await self.session.execute(
            select(SnapshotSchema)
            .where(
                and_(
                    SnapshotSchema.symbol == symbol,
                    SnapshotSchema.timeframe == timeframe,
                )
            )
            .order_by(desc(SnapshotSchema.timestamp), desc(SnapshotSchema.version))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def find_by_time_range(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        limit: Optional[int] = None,
    ) -> list[SnapshotSchema]:
        """Find snapshots within time range."""
        query = (
            select(SnapshotSchema)
            .where(
                and_(
                    SnapshotSchema.symbol == symbol,
                    SnapshotSchema.timeframe == timeframe,
                    SnapshotSchema.timestamp >= start_time,
                    SnapshotSchema.timestamp <= end_time,
                )
            )
            .order_by(SnapshotSchema.timestamp, desc(SnapshotSchema.version))
        )
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_snapshot_count(
        self,
        symbol: str,
        timeframe: str,
    ) -> int:
        """Count total snapshots for symbol/timeframe."""
        from sqlalchemy import func
        
        result = await self.session.execute(
            select(func.count(SnapshotSchema.id)).where(
                and_(
                    SnapshotSchema.symbol == symbol,
                    SnapshotSchema.timeframe == timeframe,
                )
            )
        )
        return result.scalar_one()
    
    async def delete_by_id(self, snapshot_id: UUID) -> bool:
        """Delete snapshot by ID."""
        snapshot = await self.get_by_id(snapshot_id)
        
        if not snapshot:
            return False
        
        await self.session.delete(snapshot)
        await self.session.flush()
        
        self._logger.debug(
            "snapshot_deleted",
            extra={"snapshot_id": str(snapshot_id)},
        )
        
        return True
    
    async def _get_latest_version(
        self,
        symbol: str,
        timeframe: str,
    ) -> int:
        """Get latest version number for symbol/timeframe."""
        from sqlalchemy import func
        
        result = await self.session.execute(
            select(func.max(SnapshotSchema.version)).where(
                and_(
                    SnapshotSchema.symbol == symbol,
                    SnapshotSchema.timeframe == timeframe,
                )
            )
        )
        
        max_version = result.scalar_one_or_none()
        return max_version if max_version is not None else 0
