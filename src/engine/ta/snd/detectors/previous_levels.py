from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import calculate_pips
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.snd.config import SnDConfig

logger = get_logger(__name__)


class PreviousHighsLows:
    """
    Represents clustered Previous Highs or Previous Lows.
    
    Also called Previous Fakeouts - these are resistance/support levels
    that have been tested multiple times at the same price level.
    
    Requirements (Universal Rule 2):
    - Minimum 2 clustered touches at same level
    - Single previous high/low does NOT qualify
    - Normally sits at same QML level (acts as Left Shoulder)
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str,
        level: float,
        direction: Direction,
        touches: list,
        touch_count: int,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.level = level
        self.direction = direction
        self.touches = touches
        self.touch_count = touch_count


class PreviousLevelDetector:
    """
    Detects and aggregates Previous Highs/Lows (Previous Fakeouts).
    
    Previous Highs (for sells):
    - Minimum 2 resistance touches at same level
    - Acts as Left Shoulder at QML level
    - Adds critical confluence to sell setups
    
    Previous Lows (for buys):
    - Minimum 2 support touches at same level
    - Acts as Left Shoulder at QMH level
    - Adds critical confluence to buy setups
    
    Requirements:
    - Minimum 2 touches (Universal Rule 2)
    - Touches must be within tolerance (default 3 pips)
    - More touches = stronger level
    """
    
    def __init__(self, config: SnDConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)
    
    def detect_previous_highs(
        self,
        sequence: CandleSequence,
        swing_highs: list[SwingHigh],
    ) -> list[PreviousHighsLows]:
        previous_highs = []
        
        if len(swing_highs) < self.config.min_previous_touches:
            return previous_highs
        
        clustered_highs = self._cluster_levels(
            swing_highs,
            sequence.symbol,
            Direction.BEARISH,
        )
        
        for cluster in clustered_highs:
            if cluster.touch_count >= self.config.min_previous_touches:
                previous_highs.append(cluster)
                
                self._logger.debug(
                    "previous_highs_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "level": cluster.level,
                        "touch_count": cluster.touch_count,
                    },
                )
        
        return previous_highs
    
    def detect_previous_lows(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
    ) -> list[PreviousHighsLows]:
        previous_lows = []
        
        if len(swing_lows) < self.config.min_previous_touches:
            return previous_lows
        
        clustered_lows = self._cluster_levels(
            swing_lows,
            sequence.symbol,
            Direction.BULLISH,
        )
        
        for cluster in clustered_lows:
            if cluster.touch_count >= self.config.min_previous_touches:
                previous_lows.append(cluster)
                
                self._logger.debug(
                    "previous_lows_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "level": cluster.level,
                        "touch_count": cluster.touch_count,
                    },
                )
        
        return previous_lows
    
    def _cluster_levels(
        self,
        swings: list,
        symbol: str,
        direction: Direction,
    ) -> list[PreviousHighsLows]:
        clusters = []
        processed = set()
        
        for i, swing in enumerate(swings):
            if i in processed:
                continue
            
            cluster_touches = [swing]
            processed.add(i)
            
            for j, other_swing in enumerate(swings):
                if j in processed or j == i:
                    continue
                
                price_diff_pips = calculate_pips(
                    swing.price,
                    other_swing.price,
                    symbol,
                )
                
                if abs(price_diff_pips) <= self.config.previous_level_tolerance_pips:
                    cluster_touches.append(other_swing)
                    processed.add(j)
            
            if len(cluster_touches) >= self.config.min_previous_touches:
                avg_level = sum(s.price for s in cluster_touches) / len(cluster_touches)
                
                cluster = PreviousHighsLows(
                    symbol=symbol,
                    timeframe=str(cluster_touches[0].timeframe),
                    level=avg_level,
                    direction=direction,
                    touches=cluster_touches,
                    touch_count=len(cluster_touches),
                )
                
                clusters.append(cluster)
        
        return clusters
    
    def find_previous_highs_at_qml(
        self,
        previous_highs: list[PreviousHighsLows],
        qml_level: float,
        symbol: str,
    ) -> list[PreviousHighsLows]:
        matching = []
        
        for prev_high in previous_highs:
            price_diff_pips = calculate_pips(
                prev_high.level,
                qml_level,
                symbol,
            )
            
            if abs(price_diff_pips) <= self.config.previous_level_tolerance_pips:
                matching.append(prev_high)
        
        return matching
    
    def find_previous_lows_at_qmh(
        self,
        previous_lows: list[PreviousHighsLows],
        qmh_level: float,
        symbol: str,
    ) -> list[PreviousHighsLows]:
        matching = []
        
        for prev_low in previous_lows:
            price_diff_pips = calculate_pips(
                prev_low.level,
                qmh_level,
                symbol,
            )
            
            if abs(price_diff_pips) <= self.config.previous_level_tolerance_pips:
                matching.append(prev_low)
        
        return matching
