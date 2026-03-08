from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import is_within_tolerance
from engine.ta.models.candle import CandleSequence
from engine.ta.models.swing import SwingHigh, SwingLow

logger = get_logger(__name__)


class SwingAnalyzer:
    
    def __init__(
        self,
        *,
        left_bars: int = 5,
        right_bars: int = 5,
        equal_tolerance_pips: float = 2.0,
    ) -> None:
        self.left_bars = left_bars
        self.right_bars = right_bars
        self.equal_tolerance_pips = equal_tolerance_pips
    
    def detect_swing_highs(
        self,
        sequence: CandleSequence,
    ) -> list[SwingHigh]:
        swing_highs = []
        candles = sequence.candles
        
        for i in range(self.left_bars, len(candles) - self.right_bars):
            current = candles[i]
            
            is_swing_high = True
            
            for j in range(i - self.left_bars, i):
                if candles[j].high >= current.high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                for j in range(i + 1, i + self.right_bars + 1):
                    if candles[j].high >= current.high:
                        is_swing_high = False
                        break
            
            if is_swing_high:
                is_equal = self._check_equal_high(
                    current.high,
                    swing_highs,
                    current.symbol,
                )
                
                swing_high = SwingHigh(
                    symbol=current.symbol,
                    timeframe=current.timeframe,
                    timestamp=current.timestamp,
                    price=current.high,
                    index=i,
                    strength=self._calculate_strength(candles, i, is_high=True),
                    left_bars=self.left_bars,
                    right_bars=self.right_bars,
                    is_equal_high=is_equal,
                    equal_high_tolerance_pips=self.equal_tolerance_pips if is_equal else None,
                )
                
                swing_highs.append(swing_high)
        
        return swing_highs
    
    def detect_swing_lows(
        self,
        sequence: CandleSequence,
    ) -> list[SwingLow]:
        swing_lows = []
        candles = sequence.candles
        
        for i in range(self.left_bars, len(candles) - self.right_bars):
            current = candles[i]
            
            is_swing_low = True
            
            for j in range(i - self.left_bars, i):
                if candles[j].low <= current.low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                for j in range(i + 1, i + self.right_bars + 1):
                    if candles[j].low <= current.low:
                        is_swing_low = False
                        break
            
            if is_swing_low:
                is_equal = self._check_equal_low(
                    current.low,
                    swing_lows,
                    current.symbol,
                )
                
                swing_low = SwingLow(
                    symbol=current.symbol,
                    timeframe=current.timeframe,
                    timestamp=current.timestamp,
                    price=current.low,
                    index=i,
                    strength=self._calculate_strength(candles, i, is_high=False),
                    left_bars=self.left_bars,
                    right_bars=self.right_bars,
                    is_equal_low=is_equal,
                    equal_low_tolerance_pips=self.equal_tolerance_pips if is_equal else None,
                )
                
                swing_lows.append(swing_low)
        
        return swing_lows
    
    def _calculate_strength(
        self,
        candles: list,
        index: int,
        is_high: bool,
    ) -> int:
        current = candles[index]
        strength = 1
        
        lookback = min(20, index)
        
        if is_high:
            for i in range(index - lookback, index):
                if candles[i].high < current.high:
                    strength += 1
        else:
            for i in range(index - lookback, index):
                if candles[i].low > current.low:
                    strength += 1
        
        return min(strength, 10)
    
    def _check_equal_high(
        self,
        price: float,
        existing_highs: list[SwingHigh],
        symbol: str,
    ) -> bool:
        if not existing_highs:
            return False
        
        recent_highs = existing_highs[-5:] if len(existing_highs) > 5 else existing_highs
        
        for swing_high in recent_highs:
            if is_within_tolerance(
                price,
                swing_high.price,
                self.equal_tolerance_pips,
                symbol,
            ):
                return True
        
        return False
    
    def _check_equal_low(
        self,
        price: float,
        existing_lows: list[SwingLow],
        symbol: str,
    ) -> bool:
        if not existing_lows:
            return False
        
        recent_lows = existing_lows[-5:] if len(existing_lows) > 5 else existing_lows
        
        for swing_low in recent_lows:
            if is_within_tolerance(
                price,
                swing_low.price,
                self.equal_tolerance_pips,
                symbol,
            ):
                return True
        
        return False
    
    def get_latest_swing_high(
        self,
        swing_highs: list[SwingHigh],
    ) -> Optional[SwingHigh]:
        if not swing_highs:
            return None
        return max(swing_highs, key=lambda x: x.timestamp)
    
    def get_latest_swing_low(
        self,
        swing_lows: list[SwingLow],
    ) -> Optional[SwingLow]:
        if not swing_lows:
            return None
        return max(swing_lows, key=lambda x: x.timestamp)
    
    def get_highest_swing_high(
        self,
        swing_highs: list[SwingHigh],
    ) -> Optional[SwingHigh]:
        if not swing_highs:
            return None
        return max(swing_highs, key=lambda x: x.price)
    
    def get_lowest_swing_low(
        self,
        swing_lows: list[SwingLow],
    ) -> Optional[SwingLow]:
        if not swing_lows:
            return None
        return min(swing_lows, key=lambda x: x.price)
