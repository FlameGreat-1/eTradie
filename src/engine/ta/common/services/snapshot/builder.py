from datetime import datetime
from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.swings import SwingAnalyzer
from engine.ta.common.analyzers.session import SessionAnalyzer
from engine.ta.common.analyzers.liquidity import LiquidityAnalyzer
from engine.ta.common.analyzers.sweeps import SweepAnalyzer
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.analyzers.dealing_range import DealingRangeAnalyzer
from engine.ta.constants import Timeframe, Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.snapshot import TechnicalSnapshot
from engine.ta.models.structure_event import (
    BreakOfStructure,
    ChangeOfCharacter,
    BreakInMarketStructure,
    ShiftInMarketStructure,
    SRFlip,
    RSFlip,
)
from engine.ta.models.liquidity_event import (
    LiquiditySweep,
    LiquidityGrab,
    InducementEvent,
    EqualHighsLows,
)
from engine.ta.models.zone import (
    OrderBlock,
    FairValueGap,
    BreakerBlock,
    SupplyZone,
    DemandZone,
    QuasiModoLevel,
    MiniPriceLevel,
)
from engine.ta.models.fibonacci import FibonacciRetracement, DealingRange
from engine.ta.models.session import SessionState
from engine.ta.models.candidate import TechnicalCandidate

logger = get_logger(__name__)


class SnapshotBuilder:
    
    def __init__(
        self,
        swing_analyzer: SwingAnalyzer,
        session_analyzer: SessionAnalyzer,
        liquidity_analyzer: LiquidityAnalyzer,
        sweep_analyzer: SweepAnalyzer,
        fibonacci_analyzer: FibonacciAnalyzer,
        dealing_range_analyzer: DealingRangeAnalyzer,
    ) -> None:
        self.swing_analyzer = swing_analyzer
        self.session_analyzer = session_analyzer
        self.liquidity_analyzer = liquidity_analyzer
        self.sweep_analyzer = sweep_analyzer
        self.fibonacci_analyzer = fibonacci_analyzer
        self.dealing_range_analyzer = dealing_range_analyzer
        self._logger = get_logger(__name__)
    
    def build_snapshot(
        self,
        candles: CandleSequence,
        bos_events: Optional[list[BreakOfStructure]] = None,
        choch_events: Optional[list[ChangeOfCharacter]] = None,
        bms_events: Optional[list[BreakInMarketStructure]] = None,
        sms_events: Optional[list[ShiftInMarketStructure]] = None,
        sr_flips: Optional[list[SRFlip]] = None,
        rs_flips: Optional[list[RSFlip]] = None,
        liquidity_sweeps: Optional[list[LiquiditySweep]] = None,
        liquidity_grabs: Optional[list[LiquidityGrab]] = None,
        inducement_events: Optional[list[InducementEvent]] = None,
        equal_highs_lows: Optional[list[EqualHighsLows]] = None,
        order_blocks: Optional[list[OrderBlock]] = None,
        fvgs: Optional[list[FairValueGap]] = None,
        breaker_blocks: Optional[list[BreakerBlock]] = None,
        supply_zones: Optional[list[SupplyZone]] = None,
        demand_zones: Optional[list[DemandZone]] = None,
        qml_levels: Optional[list[QuasiModoLevel]] = None,
        mpl_levels: Optional[list[MiniPriceLevel]] = None,
        fibonacci_retracements: Optional[list[FibonacciRetracement]] = None,
        dealing_ranges: Optional[list[DealingRange]] = None,
        candidates: Optional[list[TechnicalCandidate]] = None,
        metadata: Optional[dict] = None,
    ) -> TechnicalSnapshot:
        swing_highs = self.swing_analyzer.detect_swing_highs(candles)
        swing_lows = self.swing_analyzer.detect_swing_lows(candles)
        
        latest_candle = candles.candles[-1]
        session_state = self.session_analyzer.identify_session(latest_candle.timestamp)
        
        trend_direction = self._determine_trend_direction(
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            bos_events=bos_events or [],
            choch_events=choch_events or [],
        )
        
        snapshot = TechnicalSnapshot(
            symbol=candles.symbol,
            timeframe=candles.timeframe,
            timestamp=latest_candle.timestamp,
            candles=candles,
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            bos_events=bos_events or [],
            choch_events=choch_events or [],
            bms_events=bms_events or [],
            sms_events=sms_events or [],
            sr_flips=sr_flips or [],
            rs_flips=rs_flips or [],
            liquidity_sweeps=liquidity_sweeps or [],
            liquidity_grabs=liquidity_grabs or [],
            inducement_events=inducement_events or [],
            equal_highs_lows=equal_highs_lows or [],
            order_blocks=order_blocks or [],
            fvgs=fvgs or [],
            breaker_blocks=breaker_blocks or [],
            supply_zones=supply_zones or [],
            demand_zones=demand_zones or [],
            qml_levels=qml_levels or [],
            mpl_levels=mpl_levels or [],
            fibonacci_retracements=fibonacci_retracements or [],
            dealing_ranges=dealing_ranges or [],
            session_state=session_state,
            trend_direction=trend_direction,
            candidates=candidates or [],
            metadata=metadata or {},
        )
        
        self._logger.info(
            "snapshot_built",
            extra={
                "symbol": candles.symbol,
                "timeframe": candles.timeframe,
                "candle_count": candles.count,
                "swing_highs": len(swing_highs),
                "swing_lows": len(swing_lows),
                "total_structure_events": snapshot.total_structure_events,
                "total_liquidity_events": snapshot.total_liquidity_events,
                "total_zones": snapshot.total_zones,
                "total_candidates": snapshot.total_candidates,
                "trend_direction": trend_direction,
            },
        )
        
        return snapshot
    
    def _determine_trend_direction(
        self,
        swing_highs: list,
        swing_lows: list,
        bos_events: list[BreakOfStructure],
        choch_events: list[ChangeOfCharacter],
    ) -> Direction:
        if not swing_highs or not swing_lows:
            return Direction.NEUTRAL
        
        latest_bos = max(bos_events, key=lambda x: x.timestamp) if bos_events else None
        latest_choch = max(choch_events, key=lambda x: x.timestamp) if choch_events else None
        
        if latest_bos and latest_choch:
            if latest_bos.timestamp > latest_choch.timestamp:
                return latest_bos.direction
            else:
                return latest_choch.direction
        elif latest_bos:
            return latest_bos.direction
        elif latest_choch:
            return latest_choch.direction
        
        recent_highs = sorted(swing_highs, key=lambda x: x.timestamp)[-3:]
        recent_lows = sorted(swing_lows, key=lambda x: x.timestamp)[-3:]
        
        if len(recent_highs) >= 2:
            higher_highs = all(
                recent_highs[i].price > recent_highs[i - 1].price
                for i in range(1, len(recent_highs))
            )
            if higher_highs:
                return Direction.BULLISH
        
        if len(recent_lows) >= 2:
            lower_lows = all(
                recent_lows[i].price < recent_lows[i - 1].price
                for i in range(1, len(recent_lows))
            )
            if lower_lows:
                return Direction.BEARISH
        
        return Direction.NEUTRAL
