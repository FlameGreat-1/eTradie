from typing import Optional
from datetime import datetime

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.session import SessionAnalyzer
from engine.ta.common.analyzers.dealing_range import DealingRangeAnalyzer
from engine.ta.constants import Session, Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import DealingRange
from engine.ta.models.session import SessionRange
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class AMDPhase:
    """AMD Phase enumeration."""
    ACCUMULATION = "ACCUMULATION"
    MANIPULATION = "MANIPULATION"
    DISTRIBUTION = "DISTRIBUTION"


class AMDContext:
    """
    AMD (Accumulation, Manipulation, Distribution) context.
    
    AMD Pattern (Pattern 4/9):
    - Accumulation: Asian session consolidates and builds a range
    - Manipulation: London/NY open manipulates price above/below Asian range to trap traders
    - Distribution: Price reverses hard in true direction
    
    Entry during Distribution using: Simple RTO to OB, SH+BMS+RTO, SMS+BMS+RTO
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str,
        timestamp: datetime,
        phase: str,
        asian_range: Optional[DealingRange],
        manipulation_direction: Optional[Direction],
        distribution_direction: Optional[Direction],
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.timestamp = timestamp
        self.phase = phase
        self.asian_range = asian_range
        self.manipulation_direction = manipulation_direction
        self.distribution_direction = distribution_direction


class AMDDetector:
    """
    Detects AMD (Accumulation, Manipulation, Distribution) phases.
    
    AMD Requirements (Universal Rule 8):
    - Accumulation: Asian session range (consolidation)
    - Manipulation: London/NY open false move above/below Asian range
    - Distribution: True directional move (reversal from manipulation)
    
    Only enter during Distribution phase after Manipulation completes.
    """
    
    def __init__(
        self,
        config: SMCConfig,
        session_analyzer: SessionAnalyzer,
        dealing_range_analyzer: DealingRangeAnalyzer,
    ) -> None:
        self.config = config
        self.session_analyzer = session_analyzer
        self.dealing_range_analyzer = dealing_range_analyzer
        self._logger = get_logger(__name__)
    
    def detect_amd_context(
        self,
        sequence: CandleSequence,
    ) -> Optional[AMDContext]:
        asian_range = self._extract_asian_range(sequence)
        
        if not asian_range:
            return None
        
        manipulation_detected, manipulation_direction = self._detect_manipulation(
            sequence,
            asian_range,
        )
        
        if not manipulation_detected:
            return AMDContext(
                symbol=sequence.symbol,
                timeframe=str(sequence.timeframe),
                timestamp=sequence.candles[-1].timestamp,
                phase=AMDPhase.ACCUMULATION,
                asian_range=asian_range,
                manipulation_direction=None,
                distribution_direction=None,
            )
        
        distribution_detected, distribution_direction = self._detect_distribution(
            sequence,
            asian_range,
            manipulation_direction,
        )
        
        if not distribution_detected:
            return AMDContext(
                symbol=sequence.symbol,
                timeframe=str(sequence.timeframe),
                timestamp=sequence.candles[-1].timestamp,
                phase=AMDPhase.MANIPULATION,
                asian_range=asian_range,
                manipulation_direction=manipulation_direction,
                distribution_direction=None,
            )
        
        self._logger.info(
            "amd_distribution_phase_detected",
            extra={
                "symbol": sequence.symbol,
                "timeframe": sequence.timeframe,
                "manipulation_direction": str(manipulation_direction),
                "distribution_direction": str(distribution_direction),
            },
        )
        
        return AMDContext(
            symbol=sequence.symbol,
            timeframe=str(sequence.timeframe),
            timestamp=sequence.candles[-1].timestamp,
            phase=AMDPhase.DISTRIBUTION,
            asian_range=asian_range,
            manipulation_direction=manipulation_direction,
            distribution_direction=distribution_direction,
        )
    
    def _extract_asian_range(
        self,
        sequence: CandleSequence,
    ) -> Optional[DealingRange]:
        asian_range = self.session_analyzer.extract_session_range(
            sequence,
            Session.ASIA,
        )
        
        if not asian_range:
            return None
        
        dealing_range = self.dealing_range_analyzer.create_from_session(asian_range)
        
        return dealing_range
    
    def _detect_manipulation(
        self,
        sequence: CandleSequence,
        asian_range: DealingRange,
    ) -> tuple[bool, Optional[Direction]]:
        london_candles = self.session_analyzer.get_session_candles(
            sequence,
            Session.LONDON,
        )
        
        ny_candles = self.session_analyzer.get_session_candles(
            sequence,
            Session.NEW_YORK,
        )
        
        manipulation_candles = london_candles + ny_candles
        
        if not manipulation_candles:
            return False, None
        
        for candle in manipulation_candles:
            if candle.high > asian_range.high:
                return True, Direction.BULLISH
            
            if candle.low < asian_range.low:
                return True, Direction.BEARISH
        
        return False, None
    
    def _detect_distribution(
        self,
        sequence: CandleSequence,
        asian_range: DealingRange,
        manipulation_direction: Optional[Direction],
    ) -> tuple[bool, Optional[Direction]]:
        if not manipulation_direction:
            return False, None
        
        london_candles = self.session_analyzer.get_session_candles(
            sequence,
            Session.LONDON,
        )
        
        ny_candles = self.session_analyzer.get_session_candles(
            sequence,
            Session.NEW_YORK,
        )
        
        distribution_candles = london_candles + ny_candles
        
        if not distribution_candles:
            return False, None
        
        if manipulation_direction == Direction.BULLISH:
            for candle in distribution_candles:
                if candle.close < asian_range.equilibrium:
                    return True, Direction.BEARISH
        
        elif manipulation_direction == Direction.BEARISH:
            for candle in distribution_candles:
                if candle.close > asian_range.equilibrium:
                    return True, Direction.BULLISH
        
        return False, None
