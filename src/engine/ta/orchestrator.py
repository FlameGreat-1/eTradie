from datetime import datetime, timedelta
from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.broker.base import BaseBrokerClient
from engine.ta.common.analyzers.candles import CandleAnalyzer
from engine.ta.common.analyzers.swings import SwingAnalyzer
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.services.snapshot.builder import SnapshotBuilder
from engine.ta.constants import Timeframe
from engine.ta.models.candle import CandleSequence, Candle
from engine.ta.models.candidate import SMCCandidate, SnDCandidate
from engine.ta.models.snapshot import TechnicalSnapshot
from engine.ta.smc.detector import SMCDetector
from engine.ta.snd.detector import SnDDetector
from engine.ta.storage.repositories.candle import CandleRepository
from engine.ta.storage.repositories.snapshot import SnapshotRepository
from engine.ta.storage.repositories.candidate import CandidateRepository

logger = get_logger(__name__)


class TAOrchestrator:
    """
    TA workflow orchestration.
    
    Coordinates:
    1. Candle fetching from broker
    2. CandleSequence building
    3. SMC pattern detection
    4. SnD pattern detection
    5. TechnicalSnapshot creation
    6. Persistence (candles, snapshots, candidates)
    7. Error handling and metrics
    """
    
    def __init__(
        self,
        broker_client: BaseBrokerClient,
        candle_repository: CandleRepository,
        snapshot_repository: SnapshotRepository,
        candidate_repository: CandidateRepository,
        smc_detector: SMCDetector,
        snd_detector: SnDDetector,
        snapshot_builder: SnapshotBuilder,
        candle_analyzer: CandleAnalyzer,
        swing_analyzer: SwingAnalyzer,
        fibonacci_analyzer: FibonacciAnalyzer,
    ) -> None:
        self.broker_client = broker_client
        self.candle_repository = candle_repository
        self.snapshot_repository = snapshot_repository
        self.candidate_repository = candidate_repository
        self.smc_detector = smc_detector
        self.snd_detector = snd_detector
        self.snapshot_builder = snapshot_builder
        self.candle_analyzer = candle_analyzer
        self.swing_analyzer = swing_analyzer
        self.fibonacci_analyzer = fibonacci_analyzer
        self._logger = get_logger(__name__)
    
    async def analyze(
        self,
        symbol: str,
        htf_timeframe: Timeframe,
        ltf_timeframe: Timeframe,
        lookback_periods: int = 500,
    ) -> dict:
        """
        Main orchestration method.
        
        Executes complete TA workflow:
        1. Fetch HTF and LTF candles
        2. Build CandleSequences
        3. Run SMC detection
        4. Run SnD detection
        5. Build TechnicalSnapshot
        6. Persist all results
        """
        self._logger.info(
            "ta_analysis_started",
            extra={
                "symbol": symbol,
                "htf_timeframe": htf_timeframe.value,
                "ltf_timeframe": ltf_timeframe.value,
            },
        )
        
        try:
            htf_sequence = await self._fetch_and_build_sequence(
                symbol,
                htf_timeframe,
                lookback_periods,
            )
            
            ltf_sequence = await self._fetch_and_build_sequence(
                symbol,
                ltf_timeframe,
                lookback_periods * 4,
            )
            
            if not htf_sequence or not ltf_sequence:
                self._logger.warning(
                    "ta_analysis_insufficient_data",
                    extra={"symbol": symbol},
                )
                return {
                    "status": "insufficient_data",
                    "smc_candidates": 0,
                    "snd_candidates": 0,
                }
            
            smc_candidates = await self._run_smc_detection(
                htf_sequence,
                ltf_sequence,
            )
            
            snd_candidates = await self._run_snd_detection(
                htf_sequence,
                ltf_sequence,
            )
            
            snapshot = await self._build_snapshot(
                htf_sequence,
                ltf_sequence,
            )
            
            await self._persist_results(
                snapshot,
                smc_candidates,
                snd_candidates,
            )
            
            self._logger.info(
                "ta_analysis_completed",
                extra={
                    "symbol": symbol,
                    "htf_timeframe": htf_timeframe.value,
                    "ltf_timeframe": ltf_timeframe.value,
                    "smc_candidates": len(smc_candidates),
                    "snd_candidates": len(snd_candidates),
                },
            )
            
            return {
                "status": "success",
                "smc_candidates": len(smc_candidates),
                "snd_candidates": len(snd_candidates),
                "snapshot_id": str(snapshot.id) if hasattr(snapshot, 'id') else None,
            }
        
        except Exception as e:
            self._logger.error(
                "ta_analysis_failed",
                extra={
                    "symbol": symbol,
                    "htf_timeframe": htf_timeframe.value,
                    "ltf_timeframe": ltf_timeframe.value,
                    "error": str(e),
                },
                exc_info=True,
            )
            return {
                "status": "error",
                "error": str(e),
                "smc_candidates": 0,
                "snd_candidates": 0,
            }
    
    async def _fetch_and_build_sequence(
        self,
        symbol: str,
        timeframe: Timeframe,
        lookback_periods: int,
    ) -> Optional[CandleSequence]:
        """Fetch candles and build CandleSequence."""
        end_time = datetime.utcnow()
        start_time = self._calculate_start_time(end_time, timeframe, lookback_periods)
        
        stored_candles = await self.candle_repository.find_by_time_range(
            symbol,
            timeframe.value,
            start_time,
            end_time,
        )
        
        if len(stored_candles) < lookback_periods * 0.8:
            self._logger.info(
                "fetching_candles_from_broker",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe.value,
                    "stored_count": len(stored_candles),
                    "required_count": lookback_periods,
                },
            )
            
            broker_candles = await self.broker_client.fetch_historical_candles(
                symbol,
                timeframe.value,
                start_time,
                end_time,
            )
            
            if broker_candles:
                new_candles = []
                for candle in broker_candles:
                    existing = await self.candle_repository.find_by_symbol_timeframe_timestamp(
                        symbol,
                        timeframe.value,
                        candle.timestamp,
                    )
                    if not existing:
                        new_candles.append(candle)
                
                if new_candles:
                    await self.candle_repository.bulk_create(new_candles)
                    stored_candles = await self.candle_repository.find_by_time_range(
                        symbol,
                        timeframe.value,
                        start_time,
                        end_time,
                    )
        
        if not stored_candles:
            return None
        
        candles = [
            Candle(
                symbol=c.symbol,
                timeframe=c.timeframe,
                open_time=c.open_time,
                close_time=c.close_time,
                timestamp=c.timestamp,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
            )
            for c in stored_candles
        ]
        
        return CandleSequence(
            symbol=symbol,
            timeframe=timeframe.value,
            candles=candles,
        )
    
    def _calculate_start_time(
        self,
        end_time: datetime,
        timeframe: Timeframe,
        lookback_periods: int,
    ) -> datetime:
        """Calculate start time based on timeframe and lookback periods."""
        if timeframe == Timeframe.M1:
            return end_time - timedelta(minutes=lookback_periods)
        elif timeframe == Timeframe.M5:
            return end_time - timedelta(minutes=5 * lookback_periods)
        elif timeframe == Timeframe.M15:
            return end_time - timedelta(minutes=15 * lookback_periods)
        elif timeframe == Timeframe.M30:
            return end_time - timedelta(minutes=30 * lookback_periods)
        elif timeframe == Timeframe.H1:
            return end_time - timedelta(hours=lookback_periods)
        elif timeframe == Timeframe.H4:
            return end_time - timedelta(hours=4 * lookback_periods)
        elif timeframe == Timeframe.D1:
            return end_time - timedelta(days=lookback_periods)
        else:
            return end_time - timedelta(hours=lookback_periods)

    async def _run_smc_detection(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
    ) -> list[SMCCandidate]:
        """Run SMC pattern detection."""
        self._logger.debug(
            "smc_detection_started",
            extra={
                "symbol": htf_sequence.symbol,
                "htf_timeframe": htf_sequence.timeframe,
                "ltf_timeframe": ltf_sequence.timeframe,
            },
        )
        
        try:
            candidates = self.smc_detector.detect_patterns(
                htf_sequence,
                ltf_sequence,
            )
            
            self._logger.debug(
                "smc_detection_completed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "candidates_count": len(candidates),
                },
            )
            
            return candidates
        
        except Exception as e:
            self._logger.error(
                "smc_detection_failed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "error": str(e),
                },
                exc_info=True,
            )
            return []
    
    async def _run_snd_detection(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
    ) -> list[SnDCandidate]:
        """Run SnD pattern detection."""
        self._logger.debug(
            "snd_detection_started",
            extra={
                "symbol": htf_sequence.symbol,
                "htf_timeframe": htf_sequence.timeframe,
                "ltf_timeframe": ltf_sequence.timeframe,
            },
        )
        
        try:
            candidates = self.snd_detector.detect_patterns(
                htf_sequence,
                ltf_sequence,
            )
            
            self._logger.debug(
                "snd_detection_completed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "candidates_count": len(candidates),
                },
            )
            
            return candidates
        
        except Exception as e:
            self._logger.error(
                "snd_detection_failed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "error": str(e),
                },
                exc_info=True,
            )
            return []
    
    async def _build_snapshot(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
    ) -> TechnicalSnapshot:
        """Build TechnicalSnapshot from detected primitives."""
        self._logger.debug(
            "snapshot_build_started",
            extra={
                "symbol": htf_sequence.symbol,
                "htf_timeframe": htf_sequence.timeframe,
            },
        )
        
        try:
            snapshot = self.snapshot_builder.build(
                htf_sequence,
                ltf_sequence,
            )
            
            self._logger.debug(
                "snapshot_build_completed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "swing_highs": len(snapshot.swing_highs),
                    "swing_lows": len(snapshot.swing_lows),
                },
            )
            
            return snapshot
        
        except Exception as e:
            self._logger.error(
                "snapshot_build_failed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "error": str(e),
                },
                exc_info=True,
            )
            return TechnicalSnapshot(
                symbol=htf_sequence.symbol,
                timeframe=htf_sequence.timeframe,
                timestamp=datetime.utcnow(),
                swing_highs=[],
                swing_lows=[],
                bms_events=[],
                choch_events=[],
                sms_events=[],
                order_blocks=[],
                fair_value_gaps=[],
                liquidity_sweeps=[],
                inducement_events=[],
            )
    
    async def _persist_results(
        self,
        snapshot: TechnicalSnapshot,
        smc_candidates: list[SMCCandidate],
        snd_candidates: list[SnDCandidate],
    ) -> None:
        """Persist snapshot and candidates to storage."""
        try:
            await self._persist_snapshot(snapshot)
            await self._persist_smc_candidates(smc_candidates)
            await self._persist_snd_candidates(snd_candidates)
            
            self._logger.debug(
                "persistence_completed",
                extra={
                    "symbol": snapshot.symbol,
                    "smc_candidates": len(smc_candidates),
                    "snd_candidates": len(snd_candidates),
                },
            )
        
        except Exception as e:
            self._logger.error(
                "persistence_failed",
                extra={
                    "symbol": snapshot.symbol,
                    "error": str(e),
                },
                exc_info=True,
            )
    
    async def _persist_snapshot(self, snapshot: TechnicalSnapshot) -> None:
        """Persist TechnicalSnapshot to storage."""
        try:
            await self.snapshot_repository.create(
                symbol=snapshot.symbol,
                timeframe=snapshot.timeframe,
                timestamp=snapshot.timestamp,
                swing_highs=self._serialize_swing_highs(snapshot.swing_highs),
                swing_lows=self._serialize_swing_lows(snapshot.swing_lows),
                bms_events=self._serialize_bms_events(snapshot.bms_events),
                choch_events=self._serialize_choch_events(snapshot.choch_events),
                sms_events=self._serialize_sms_events(snapshot.sms_events),
                order_blocks=self._serialize_order_blocks(snapshot.order_blocks),
                fair_value_gaps=self._serialize_fvgs(snapshot.fair_value_gaps),
                liquidity_sweeps=self._serialize_sweeps(snapshot.liquidity_sweeps),
                inducement_events=self._serialize_inducements(snapshot.inducement_events),
                qm_levels={},
                sr_flips={},
                rs_flips={},
                previous_levels={},
                mpl_levels={},
                fakeout_tests={},
                supply_zones={},
                demand_zones={},
                fibonacci_retracements={},
            )
        
        except Exception as e:
            self._logger.error(
                "snapshot_persistence_failed",
                extra={
                    "symbol": snapshot.symbol,
                    "error": str(e),
                },
                exc_info=True,
            )
    
    async def _persist_smc_candidates(self, candidates: list[SMCCandidate]) -> None:
        """Persist SMC candidates to storage."""
        for candidate in candidates:
            try:
                await self.candidate_repository.create_smc_candidate(candidate)
            except Exception as e:
                self._logger.error(
                    "smc_candidate_persistence_failed",
                    extra={
                        "symbol": candidate.symbol,
                        "pattern": candidate.pattern.value,
                        "error": str(e),
                    },
                    exc_info=True,
                )
    
    async def _persist_snd_candidates(self, candidates: list[SnDCandidate]) -> None:
        """Persist SnD candidates to storage."""
        for candidate in candidates:
            try:
                await self.candidate_repository.create_snd_candidate(candidate)
            except Exception as e:
                self._logger.error(
                    "snd_candidate_persistence_failed",
                    extra={
                        "symbol": candidate.symbol,
                        "pattern": candidate.pattern.value,
                        "error": str(e),
                    },
                    exc_info=True,
                )
    
    def _serialize_swing_highs(self, swing_highs: list) -> dict:
        """Serialize swing highs for JSON storage."""
        return {
            "count": len(swing_highs),
            "data": [
                {
                    "price": sh.price,
                    "timestamp": sh.timestamp.isoformat(),
                    "index": sh.index,
                }
                for sh in swing_highs
            ],
        }
    
    def _serialize_swing_lows(self, swing_lows: list) -> dict:
        """Serialize swing lows for JSON storage."""
        return {
            "count": len(swing_lows),
            "data": [
                {
                    "price": sl.price,
                    "timestamp": sl.timestamp.isoformat(),
                    "index": sl.index,
                }
                for sl in swing_lows
            ],
        }
    
    def _serialize_bms_events(self, bms_events: list) -> dict:
        """Serialize BMS events for JSON storage."""
        return {
            "count": len(bms_events),
            "data": [
                {
                    "price": bms.price,
                    "timestamp": bms.timestamp.isoformat(),
                    "direction": bms.direction.value,
                }
                for bms in bms_events
            ],
        }
    
    def _serialize_choch_events(self, choch_events: list) -> dict:
        """Serialize CHOCH events for JSON storage."""
        return {
            "count": len(choch_events),
            "data": [
                {
                    "price": choch.price,
                    "timestamp": choch.timestamp.isoformat(),
                    "direction": choch.direction.value,
                }
                for choch in choch_events
            ],
        }
    
    def _serialize_sms_events(self, sms_events: list) -> dict:
        """Serialize SMS events for JSON storage."""
        return {
            "count": len(sms_events),
            "data": [
                {
                    "price": sms.price,
                    "timestamp": sms.timestamp.isoformat(),
                    "direction": sms.direction.value,
                }
                for sms in sms_events
            ],
        }
    
    def _serialize_order_blocks(self, order_blocks: list) -> dict:
        """Serialize order blocks for JSON storage."""
        return {
            "count": len(order_blocks),
            "data": [
                {
                    "upper_bound": ob.upper_bound,
                    "lower_bound": ob.lower_bound,
                    "timestamp": ob.timestamp.isoformat(),
                    "direction": ob.direction.value,
                }
                for ob in order_blocks
            ],
        }
    
    def _serialize_fvgs(self, fvgs: list) -> dict:
        """Serialize FVGs for JSON storage."""
        return {
            "count": len(fvgs),
            "data": [
                {
                    "upper_bound": fvg.upper_bound,
                    "lower_bound": fvg.lower_bound,
                    "timestamp": fvg.timestamp.isoformat(),
                    "direction": fvg.direction.value,
                }
                for fvg in fvgs
            ],
        }
    
    def _serialize_sweeps(self, sweeps: list) -> dict:
        """Serialize liquidity sweeps for JSON storage."""
        return {
            "count": len(sweeps),
            "data": [
                {
                    "swept_level": sweep.swept_level,
                    "timestamp": sweep.timestamp.isoformat(),
                    "direction": sweep.direction.value,
                }
                for sweep in sweeps
            ],
        }
    
    def _serialize_inducements(self, inducements: list) -> dict:
        """Serialize inducement events for JSON storage."""
        return {
            "count": len(inducements),
            "data": [
                {
                    "price": ind.price,
                    "timestamp": ind.timestamp.isoformat(),
                    "direction": ind.direction.value,
                }
                for ind in inducements
            ],
        }
