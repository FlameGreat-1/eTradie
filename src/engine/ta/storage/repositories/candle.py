from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from engine.shared.logging import get_logger
from engine.ta.models.candle import Candle
from engine.ta.storage.schemas.candle import CandleSchema

logger = get_logger(__name__)


class CandleRepository:
    """
    Repository for candle persistence, cache snapshots, and historical retrieval.
    
    Provides:
    - Historical candle storage (immutable after insert)
    - Cache snapshots for quick retrieval
    - Backfill support for missing data
    - Efficient batch operations
    - Time-range queries
    
    All operations are async for non-blocking I/O.
    """
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._logger = get_logger(__name__)
    
    async def create(self, candle: Candle) -> CandleSchema:
        """Create a single candle record."""
        schema = CandleSchema(
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            open_time=candle.open_time,
            close_time=candle.close_time,
            timestamp=candle.timestamp,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            quote_volume=candle.quote_volume,
            number_of_trades=candle.number_of_trades,
            taker_buy_base_volume=candle.taker_buy_base_volume,
            taker_buy_quote_volume=candle.taker_buy_quote_volume,
        )
        
        self.session.add(schema)
        await self.session.flush()
        
        self._logger.debug(
            "candle_created",
            extra={
                "symbol": candle.symbol,
                "timeframe": candle.timeframe,
                "timestamp": candle.timestamp.isoformat(),
            },
        )
        
        return schema
    
    async def bulk_create(self, candles: list[Candle]) -> list[CandleSchema]:
        """Batch insert multiple candles."""
        schemas = [
            CandleSchema(
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                open_time=candle.open_time,
                close_time=candle.close_time,
                timestamp=candle.timestamp,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
                quote_volume=candle.quote_volume,
                number_of_trades=candle.number_of_trades,
                taker_buy_base_volume=candle.taker_buy_base_volume,
                taker_buy_quote_volume=candle.taker_buy_quote_volume,
            )
            for candle in candles
        ]
        
        self.session.add_all(schemas)
        await self.session.flush()
        
        self._logger.info(
            "candles_bulk_created",
            extra={
                "count": len(candles),
                "symbol": candles[0].symbol if candles else None,
                "timeframe": candles[0].timeframe if candles else None,
            },
        )
        
        return schemas
    
    async def get_by_id(self, candle_id: UUID) -> Optional[CandleSchema]:
        """Retrieve candle by ID."""
        result = await self.session.execute(
            select(CandleSchema).where(CandleSchema.id == candle_id)
        )
        return result.scalar_one_or_none()
    
    async def find_by_symbol_timeframe_timestamp(
        self,
        symbol: str,
        timeframe: str,
        timestamp: datetime,
    ) -> Optional[CandleSchema]:
        """Find candle by symbol, timeframe, and timestamp."""
        result = await self.session.execute(
            select(CandleSchema).where(
                and_(
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
        limit: Optional[int] = None,
    ) -> list[CandleSchema]:
        """Find candles within time range."""
        query = select(CandleSchema).where(
            and_(
                CandleSchema.symbol == symbol,
                CandleSchema.timeframe == timeframe,
                CandleSchema.timestamp >= start_time,
                CandleSchema.timestamp <= end_time,
            )
        ).order_by(CandleSchema.timestamp)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_latest_candle(
        self,
        symbol: str,
        timeframe: str,
    ) -> Optional[CandleSchema]:
        """Get most recent candle for symbol/timeframe."""
        result = await self.session.execute(
            select(CandleSchema)
            .where(
                and_(
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
    ) -> int:
        """Count total candles for symbol/timeframe."""
        from sqlalchemy import func
        
        result = await self.session.execute(
            select(func.count(CandleSchema.id)).where(
                and_(
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
    ) -> int:
        """Delete candles within time range. Returns count deleted."""
        from sqlalchemy import delete
        
        result = await self.session.execute(
            delete(CandleSchema).where(
                and_(
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
