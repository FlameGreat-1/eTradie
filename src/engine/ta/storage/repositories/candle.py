from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.shared.logging import get_logger
from engine.ta.constants import TIMEFRAME_MINUTES, Timeframe
from engine.ta.models.candle import Candle
from engine.ta.storage.schemas.candle import CandleSchema

logger = get_logger(__name__)


def _derive_close_time(timestamp: datetime, timeframe_str: str) -> datetime:
    """Derive candle close time from open timestamp + timeframe duration."""
    try:
        tf = Timeframe(timeframe_str)
        minutes = TIMEFRAME_MINUTES.get(tf)
        if minutes is not None:
            return timestamp + timedelta(minutes=minutes)
    except (ValueError, KeyError):
        pass
    # Fallback: assume 1-minute candle.
    return timestamp + timedelta(minutes=1)


def _candle_to_schema(candle: Candle, user_id: str) -> CandleSchema:
    """Map a Candle domain model to a CandleSchema ORM row.

    Only maps fields that exist on the Candle model. Derives
    open_time/close_time from timestamp + timeframe duration.
    Crypto-specific fields are left as None.

    Args:
        candle: The candle domain model.
        user_id: The owning user's ID. Required for multi-tenant isolation.
    """
    tf_str = candle.timeframe.value if hasattr(candle.timeframe, "value") else str(candle.timeframe)
    return CandleSchema(
        user_id=user_id,
        symbol=candle.symbol,
        timeframe=tf_str,
        timestamp=candle.timestamp,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
        open_time=candle.timestamp,
        close_time=_derive_close_time(candle.timestamp, tf_str),
    )


class CandleRepository:
    """
    Repository for candle persistence and historical retrieval.

    Provides:
    - Historical candle storage (immutable after insert)
    - Backfill support for missing data
    - Efficient batch operations
    - Time-range queries

    All operations are async for non-blocking I/O.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._logger = get_logger(__name__)

    async def create(self, candle: Candle, *, user_id: str) -> CandleSchema:
        """Create a single candle record owned by user_id."""
        schema = _candle_to_schema(candle, user_id)

        self.session.add(schema)
        await self.session.flush()

        self._logger.debug(
            "candle_created",
            extra={
                "symbol": candle.symbol,
                "timeframe": schema.timeframe,
                "timestamp": candle.timestamp.isoformat(),
            },
        )

        return schema

    async def bulk_create(self, candles: list[Candle], *, user_id: str) -> list[CandleSchema]:
        """Batch insert multiple candles owned by user_id, idempotently.

        Uses Postgres `INSERT ... ON CONFLICT DO NOTHING` against the
        unique index ix_candles_user_symbol_timeframe_timestamp so the
        repository is safe to call with overlapping ranges. Re-fetching
        the same time window after a broker reconnect, a pre-warm wave,
        or a manual backfill no longer raises UniqueViolation.

        Returns the list of CandleSchema rows ACTUALLY inserted; rows
        skipped by the conflict resolution are NOT returned. Callers
        that only need the inserted count can `len()` the result.

        Audit ref: CHECKLIST Section 2 - 'No tick / candle data
        duplication after reconnect'.
        """
        if not candles:
            return []

        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from engine.shared.metrics.prometheus import (
            BROKER_CANDLES_DEDUP_SKIPPED_TOTAL,
        )

        rows = [
            {
                "user_id": user_id,
                "symbol": c.symbol,
                "timeframe": (c.timeframe.value if hasattr(c.timeframe, "value") else str(c.timeframe)),
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "open_time": c.timestamp,
                "close_time": _derive_close_time(
                    c.timestamp,
                    (c.timeframe.value if hasattr(c.timeframe, "value") else str(c.timeframe)),
                ),
            }
            for c in candles
        ]

        stmt = (
            pg_insert(CandleSchema)
            .values(rows)
            .on_conflict_do_nothing(
                index_elements=["user_id", "symbol", "timeframe", "timestamp"],
            )
            .returning(CandleSchema)
        )
        result = await self.session.execute(stmt)
        inserted = list(result.scalars().all())
        await self.session.flush()

        skipped = len(rows) - len(inserted)
        if skipped > 0:
            BROKER_CANDLES_DEDUP_SKIPPED_TOTAL.labels(
                provider="unknown",
                symbol=candles[0].symbol,
                timeframe=rows[0]["timeframe"],
            ).inc(skipped)

        self._logger.info(
            "candles_bulk_created",
            extra={
                "requested": len(candles),
                "inserted": len(inserted),
                "deduped": skipped,
                "symbol": candles[0].symbol,
                "timeframe": rows[0]["timeframe"],
            },
        )

        return inserted

    async def get_by_id(
        self,
        candle_id: UUID,
    ) -> CandleSchema | None:
        """Retrieve candle by ID."""
        result = await self.session.execute(select(CandleSchema).where(CandleSchema.id == candle_id))
        return result.scalar_one_or_none()

    async def find_by_symbol_timeframe_timestamp(
        self,
        symbol: str,
        timeframe: str,
        timestamp: datetime,
        *,
        user_id: str,
    ) -> CandleSchema | None:
        """Find candle by user_id, symbol, timeframe, and timestamp."""
        result = await self.session.execute(
            select(CandleSchema).where(
                and_(
                    CandleSchema.user_id == user_id,
                    CandleSchema.symbol == symbol,
                    CandleSchema.timeframe == timeframe,
                    CandleSchema.timestamp == timestamp,
                )
            )
        )
        return result.scalar_one_or_none()

    async def find_by_time_range(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        limit: int | None = None,
        *,
        user_id: str,
    ) -> list[CandleSchema]:
        """Find candles within time range for a specific user, ordered by timestamp."""
        query = (
            select(CandleSchema)
            .where(
                and_(
                    CandleSchema.user_id == user_id,
                    CandleSchema.symbol == symbol,
                    CandleSchema.timeframe == timeframe,
                    CandleSchema.timestamp >= start_time,
                    CandleSchema.timestamp <= end_time,
                )
            )
            .order_by(CandleSchema.timestamp)
        )

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_candle(
        self,
        symbol: str,
        timeframe: str,
        *,
        user_id: str,
    ) -> CandleSchema | None:
        """Get most recent candle for user/symbol/timeframe."""
        result = await self.session.execute(
            select(CandleSchema)
            .where(
                and_(
                    CandleSchema.user_id == user_id,
                    CandleSchema.symbol == symbol,
                    CandleSchema.timeframe == timeframe,
                )
            )
            .order_by(desc(CandleSchema.timestamp))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_candle_count(
        self,
        symbol: str,
        timeframe: str,
        *,
        user_id: str,
    ) -> int:
        """Count total candles for user/symbol/timeframe."""
        result = await self.session.execute(
            select(func.count(CandleSchema.id)).where(
                and_(
                    CandleSchema.user_id == user_id,
                    CandleSchema.symbol == symbol,
                    CandleSchema.timeframe == timeframe,
                )
            )
        )
        return result.scalar_one()

    async def delete_by_id(self, candle_id: UUID) -> bool:
        """Delete candle by ID."""
        candle = await self.get_by_id(candle_id)

        if not candle:
            return False

        await self.session.delete(candle)
        await self.session.flush()

        self._logger.debug(
            "candle_deleted",
            extra={"candle_id": str(candle_id)},
        )

        return True

    async def delete_by_time_range(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        *,
        user_id: str,
    ) -> int:
        """Delete candles within time range for a specific user. Returns count deleted."""
        result = await self.session.execute(
            delete(CandleSchema).where(
                and_(
                    CandleSchema.user_id == user_id,
                    CandleSchema.symbol == symbol,
                    CandleSchema.timeframe == timeframe,
                    CandleSchema.timestamp >= start_time,
                    CandleSchema.timestamp <= end_time,
                )
            )
        )

        deleted_count = result.rowcount

        self._logger.info(
            "candles_deleted_by_time_range",
            extra={
                "symbol": symbol,
                "timeframe": timeframe,
                "deleted_count": deleted_count,
            },
        )

        return deleted_count
