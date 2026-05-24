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
        *,
        user_id: str,
        swing_highs: list | dict,
        swing_lows: list | dict,
        bms_events: list | dict,
        choch_events: list | dict,
        sms_events: list | dict,
        order_blocks: list | dict,
        fair_value_gaps: list | dict,
        breaker_blocks: list | dict,
        liquidity_sweeps: list | dict,
        inducement_events: list | dict,
        qm_levels: list | dict,
        sr_flips: list | dict,
        rs_flips: list | dict,
        previous_levels: list | dict,
        mpl_levels: list | dict,
        fakeout_tests: list | dict,
        supply_zones: list | dict,
        demand_zones: list | dict,
        fibonacci_retracements: list | dict,
        dealing_ranges: list | dict,
        metadata: Optional[dict] = None,
        notes: Optional[str] = None,
    ) -> SnapshotSchema:
        """Create a new technical snapshot.

        The structural-event payload kwargs accept either ``list`` or
        ``dict``. The current `_persist_snapshot` writer emits bare
        lists (the prompt + DB unified shape); historical rows on disk
        that still carry the legacy ``{"count": N, "data": [...]}``
        dict wrapper remain valid JSONB. SQLAlchemy's ``JSON`` column
        accepts both at the wire level.
        """
        latest_version = await self._get_latest_version(symbol, timeframe, user_id=user_id)

        schema = SnapshotSchema(
            user_id=user_id,
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
            breaker_blocks=breaker_blocks,
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
            dealing_ranges=dealing_ranges,
            meta_data=metadata,
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
        *,
        user_id: str,
    ) -> Optional[SnapshotSchema]:
        """Find snapshot by user_id, symbol, timeframe, and timestamp."""
        result = await self.session.execute(
            select(SnapshotSchema)
            .where(
                and_(
                    SnapshotSchema.user_id == user_id,
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
        *,
        user_id: str,
    ) -> Optional[SnapshotSchema]:
        """Get most recent snapshot for user/symbol/timeframe."""
        result = await self.session.execute(
            select(SnapshotSchema)
            .where(
                and_(
                    SnapshotSchema.user_id == user_id,
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
        *,
        user_id: str,
    ) -> list[SnapshotSchema]:
        """Find snapshots within time range for a specific user."""
        query = (
            select(SnapshotSchema)
            .where(
                and_(
                    SnapshotSchema.user_id == user_id,
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
        *,
        user_id: str,
    ) -> int:
        """Count total snapshots for user/symbol/timeframe."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(SnapshotSchema.id)).where(
                and_(
                    SnapshotSchema.user_id == user_id,
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
        *,
        user_id: str,
    ) -> int:
        """Get latest version number for user/symbol/timeframe."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.max(SnapshotSchema.version)).where(
                and_(
                    SnapshotSchema.user_id == user_id,
                    SnapshotSchema.symbol == symbol,
                    SnapshotSchema.timeframe == timeframe,
                )
            )
        )

        max_version = result.scalar_one_or_none()
        return max_version if max_version is not None else 0
