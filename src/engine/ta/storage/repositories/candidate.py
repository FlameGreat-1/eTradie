from datetime import datetime, UTC
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from engine.shared.logging import get_logger
from engine.ta.models.candidate import SMCCandidate, SnDCandidate
from engine.ta.storage.schemas.candidate import CandidateSchema

logger = get_logger(__name__)


class CandidateRepository:
    """
    Repository for SMC/SnD candidate output storage and deduplication.
    
    Provides:
    - Candidate storage (immutable once created)
    - Deduplication (same pattern not stored twice)
    - Active/inactive tracking
    - Pattern-based queries
    - Invalidation support
    
    All operations are async for non-blocking I/O.
    """
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._logger = get_logger(__name__)
    
    async def create_smc_candidate(self, candidate: SMCCandidate) -> CandidateSchema:
        """Create SMC candidate record."""
        schema = CandidateSchema(
            symbol=candidate.symbol,
            timeframe=candidate.timeframe,
            pattern=candidate.pattern.value,
            direction=candidate.direction.value,
            timestamp=candidate.timestamp,
            entry_price=candidate.entry_price,
            stop_loss=candidate.stop_loss,
            take_profit=candidate.take_profit,
            htf_timeframe=candidate.htf_timeframe,
            ltf_timeframe=candidate.ltf_timeframe,
            is_smc=True,
            is_snd=False,
            # Structure events
            sms_detected=candidate.sms_detected,
            sms_price=candidate.sms_price,
            sms_timestamp=candidate.sms_timestamp,
            bms_detected=candidate.bms_detected,
            bms_price=candidate.bms_price,
            bms_timestamp=candidate.bms_timestamp,
            choch_detected=candidate.choch_detected,
            choch_price=candidate.choch_price,
            choch_timestamp=candidate.choch_timestamp,
            # Order block
            order_block_upper=candidate.order_block_upper,
            order_block_lower=candidate.order_block_lower,
            order_block_timestamp=candidate.order_block_timestamp,
            # FVG
            fvg_upper=candidate.fvg_upper,
            fvg_lower=candidate.fvg_lower,
            fvg_timestamp=candidate.fvg_timestamp,
            # Liquidity / inducement
            liquidity_swept=candidate.liquidity_swept,
            swept_level=candidate.swept_level,
            sweep_timestamp=candidate.sweep_timestamp,
            inducement_cleared=candidate.inducement_cleared,
            inducement_level=candidate.inducement_level,
            # LTF confirmation
            ltf_confirmation=candidate.ltf_confirmation,
            ltf_confirmation_timestamp=candidate.ltf_confirmation_timestamp,
            displacement_pips=candidate.displacement_pips,
            # Fibonacci / session
            fib_level=candidate.fib_level,
            session_context=candidate.session_context,
            metadata=candidate.metadata,
        )
        
        self.session.add(schema)
        await self.session.flush()
        
        self._logger.debug(
            "smc_candidate_created",
            extra={
                "symbol": candidate.symbol,
                "pattern": candidate.pattern.value,
                "direction": candidate.direction.value,
            },
        )
        
        return schema
    
    async def create_snd_candidate(self, candidate: SnDCandidate) -> CandidateSchema:
        """Create SnD candidate record."""
        schema = CandidateSchema(
            symbol=candidate.symbol,
            timeframe=candidate.timeframe,
            pattern=candidate.pattern.value,
            direction=candidate.direction.value,
            timestamp=candidate.timestamp,
            entry_price=candidate.entry_price,
            stop_loss=candidate.stop_loss,
            take_profit=candidate.take_profit,
            htf_timeframe=candidate.htf_timeframe,
            ltf_timeframe=candidate.ltf_timeframe,
            is_smc=False,
            is_snd=True,
            # QML
            qml_detected=candidate.qml_detected,
            qml_price=candidate.qml_price,
            qml_timestamp=candidate.qml_timestamp,
            # SR / RS Flips
            sr_flip_detected=candidate.sr_flip_detected,
            sr_flip_price=candidate.sr_flip_price,
            sr_flip_timestamp=candidate.sr_flip_timestamp,
            rs_flip_detected=candidate.rs_flip_detected,
            rs_flip_price=candidate.rs_flip_price,
            rs_flip_timestamp=candidate.rs_flip_timestamp,
            # MPL
            mpl_detected=candidate.mpl_detected,
            mpl_price=candidate.mpl_price,
            mpl_timestamp=candidate.mpl_timestamp,
            # Supply / demand zones
            supply_zone_upper=candidate.supply_zone_upper,
            supply_zone_lower=candidate.supply_zone_lower,
            supply_zone_timestamp=candidate.supply_zone_timestamp,
            demand_zone_upper=candidate.demand_zone_upper,
            demand_zone_lower=candidate.demand_zone_lower,
            demand_zone_timestamp=candidate.demand_zone_timestamp,
            # Fakeout
            fakeout_detected=candidate.fakeout_detected,
            fakeout_level=candidate.fakeout_level,
            fakeout_timestamp=candidate.fakeout_timestamp,
            # Previous highs / lows
            previous_highs_count=candidate.previous_highs_count,
            previous_lows_count=candidate.previous_lows_count,
            # Marubozu
            marubozu_detected=candidate.marubozu_detected,
            marubozu_timestamp=candidate.marubozu_timestamp,
            # Compression
            compression_detected=candidate.compression_detected,
            compression_candle_count=candidate.compression_candle_count,
            # LTF confirmation
            ltf_confirmation=candidate.ltf_confirmation,
            ltf_confirmation_timestamp=candidate.ltf_confirmation_timestamp,
            # Fibonacci / session
            fib_level=candidate.fib_level,
            session_context=candidate.session_context,
            metadata=candidate.metadata,
        )
        
        self.session.add(schema)
        await self.session.flush()
        
        self._logger.debug(
            "snd_candidate_created",
            extra={
                "symbol": candidate.symbol,
                "pattern": candidate.pattern.value,
                "direction": candidate.direction.value,
            },
        )
        
        return schema
    
    async def get_by_id(self, candidate_id: UUID) -> Optional[CandidateSchema]:
        """Retrieve candidate by ID."""
        result = await self.session.execute(
            select(CandidateSchema).where(CandidateSchema.id == candidate_id)
        )
        return result.scalar_one_or_none()
    
    async def find_active_candidates(
        self,
        symbol: str,
        timeframe: Optional[str] = None,
        pattern: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> list[CandidateSchema]:
        """Find active candidates with optional filters."""
        conditions = [CandidateSchema.symbol == symbol, CandidateSchema.is_active == True]
        
        if timeframe:
            conditions.append(CandidateSchema.timeframe == timeframe)
        if pattern:
            conditions.append(CandidateSchema.pattern == pattern)
        if direction:
            conditions.append(CandidateSchema.direction == direction)
        
        result = await self.session.execute(
            select(CandidateSchema)
            .where(and_(*conditions))
            .order_by(desc(CandidateSchema.timestamp))
        )
        return list(result.scalars().all())
    
    async def find_by_time_range(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        is_active: Optional[bool] = None,
    ) -> list[CandidateSchema]:
        """Find candidates within time range."""
        conditions = [
            CandidateSchema.symbol == symbol,
            CandidateSchema.timestamp >= start_time,
            CandidateSchema.timestamp <= end_time,
        ]
        
        if is_active is not None:
            conditions.append(CandidateSchema.is_active == is_active)
        
        result = await self.session.execute(
            select(CandidateSchema)
            .where(and_(*conditions))
            .order_by(CandidateSchema.timestamp)
        )
        return list(result.scalars().all())
    
    async def invalidate_candidate(
        self,
        candidate_id: UUID,
        reason: str,
    ) -> bool:
        """Mark candidate as invalidated."""
        result = await self.session.execute(
            update(CandidateSchema)
            .where(CandidateSchema.id == candidate_id)
            .values(
                is_active=False,
                invalidated_at=datetime.now(UTC),
                invalidation_reason=reason,
            )
        )
        
        if result.rowcount > 0:
            self._logger.debug(
                "candidate_invalidated",
                extra={
                    "candidate_id": str(candidate_id),
                    "reason": reason,
                },
            )
            return True
        
        return False
    
    async def delete_by_id(self, candidate_id: UUID) -> bool:
        """Delete candidate by ID."""
        candidate = await self.get_by_id(candidate_id)
        
        if not candidate:
            return False
        
        await self.session.delete(candidate)
        await self.session.flush()
        
        self._logger.debug(
            "candidate_deleted",
            extra={"candidate_id": str(candidate_id)},
        )
        
        return True
