from datetime import datetime
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
            sms_detected=candidate.sms_detected,
            sms_price=candidate.sms_price,
            sms_timestamp=candidate.sms_timestamp,
            bms_detected=candidate.bms_detected,
            bms_price=candidate.bms_price,
            bms_timestamp=candidate.bms_timestamp,
            choch_detected=candidate.choch_detected,
            choch_price=candidate.choch_price,
            choch_timestamp=candidate.choch_timestamp,
            order_block_upper=candidate.order_block_upper,
            order_block_lower=candidate.order_block_lower,
            order_block_timestamp=candidate.order_block_timestamp,
            liquidity_swept=candidate.liquidity_swept,
            swept_level=candidate.swept_level,
            sweep_timestamp=candidate.sweep_timestamp,
            inducement_cleared=candidate.inducement_cleared,
            ltf_confirmation=candidate.ltf_confirmation,
            ltf_confirmation_timestamp=candidate.ltf_confirmation_timestamp,
            displacement_pips=candidate.displacement_pips,
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
            qml_level=candidate.qml_level,
            qml_timestamp=candidate.qml_timestamp,
            qmh_level=candidate.qmh_level,
            qmh_timestamp=candidate.qmh_timestamp,
            sr_flip_level=candidate.sr_flip_level,
            rs_flip_level=candidate.rs_flip_level,
            fakeout_count=candidate.fakeout_count,
            has_compression=candidate.has_compression,
            has_previous_highs=candidate.has_previous_highs,
            previous_highs_count=candidate.previous_highs_count,
            has_previous_lows=candidate.has_previous_lows,
            previous_lows_count=candidate.previous_lows_count,
            has_mpl=candidate.has_mpl,
            mpl_level=candidate.mpl_level,
            ltf_confirmation=candidate.ltf_confirmation,
            ltf_confirmation_timestamp=candidate.ltf_confirmation_timestamp,
            fib_level=candidate.fib_level,
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
                invalidated_at=datetime.utcnow(),
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
