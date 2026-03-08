from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.models.zone import QuasiModoLevel
from engine.ta.snd.config import SnDConfig

logger = get_logger(__name__)


class QMDetector:
    """
    Detects Quasimodo (QM) structures and QML/QMH levels.
    
    QM Structure Definition:
    - Bearish QM (QML): H → HH → break of H level = QML established
    - Bullish QM (QMH): L → LL → break of L level = QMH established
    
    QML/QMH is the target level where Supply/Demand zones are located.
    All SnD patterns revolve around price reaching the QML/QMH.
    
    Requirements:
    - Must have clear 3-swing structure (H → HH → break OR L → LL → break)
    - Break must be substantial close beyond the level (Marubozu)
    - QML sits at the first H level (for sells)
    - QMH sits at the first L level (for buys)
    """
    
    def __init__(self, config: SnDConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)
    
    def detect_qml(
        self,
        sequence: CandleSequence,
        swing_highs: list[SwingHigh],
    ) -> list[QuasiModoLevel]:
        qml_levels = []
        
        if len(swing_highs) < 2:
            return qml_levels
        
        sorted_highs = sorted(swing_highs, key=lambda x: x.timestamp)
        
        for i in range(len(sorted_highs) - 1):
            h1 = sorted_highs[i]
            h2 = sorted_highs[i + 1]
            
            if h2.price <= h1.price:
                continue
            
            break_detected = False
            break_candle_index = None
            break_timestamp = None
            
            for j in range(h2.index + 1, len(sequence.candles)):
                candle = sequence.candles[j]
                
                if candle.close < h1.price:
                    break_detected = True
                    break_candle_index = j
                    break_timestamp = candle.timestamp
                    break
            
            if not break_detected:
                continue
            
            qml = QuasiModoLevel(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                level=h1.price,
                timestamp=h1.timestamp,
                direction=Direction.BEARISH,
                h1_price=h1.price,
                h1_timestamp=h1.timestamp,
                h2_price=h2.price,
                h2_timestamp=h2.timestamp,
                break_candle_index=break_candle_index,
                break_timestamp=break_timestamp,
                is_valid=True,
            )
            
            qml_levels.append(qml)
            
            self._logger.debug(
                "qml_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "qml_level": h1.price,
                    "h1_price": h1.price,
                    "h2_price": h2.price,
                },
            )
        
        return qml_levels
    
    def detect_qmh(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
    ) -> list[QuasiModoLevel]:
        qmh_levels = []
        
        if len(swing_lows) < 2:
            return qmh_levels
        
        sorted_lows = sorted(swing_lows, key=lambda x: x.timestamp)
        
        for i in range(len(sorted_lows) - 1):
            l1 = sorted_lows[i]
            l2 = sorted_lows[i + 1]
            
            if l2.price >= l1.price:
                continue
            
            break_detected = False
            break_candle_index = None
            break_timestamp = None
            
            for j in range(l2.index + 1, len(sequence.candles)):
                candle = sequence.candles[j]
                
                if candle.close > l1.price:
                    break_detected = True
                    break_candle_index = j
                    break_timestamp = candle.timestamp
                    break
            
            if not break_detected:
                continue
            
            qmh = QuasiModoLevel(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                level=l1.price,
                timestamp=l1.timestamp,
                direction=Direction.BULLISH,
                h1_price=l1.price,
                h1_timestamp=l1.timestamp,
                h2_price=l2.price,
                h2_timestamp=l2.timestamp,
                break_candle_index=break_candle_index,
                break_timestamp=break_timestamp,
                is_valid=True,
            )
            
            qmh_levels.append(qmh)
            
            self._logger.debug(
                "qmh_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe,
                    "qmh_level": l1.price,
                    "l1_price": l1.price,
                    "l2_price": l2.price,
                },
            )
        
        return qmh_levels
    
    def get_latest_qml(
        self,
        qml_levels: list[QuasiModoLevel],
    ) -> Optional[QuasiModoLevel]:
        if not qml_levels:
            return None
        
        valid_qmls = [qml for qml in qml_levels if qml.is_valid]
        
        if not valid_qmls:
            return None
        
        return max(valid_qmls, key=lambda x: x.timestamp)
    
    def get_latest_qmh(
        self,
        qmh_levels: list[QuasiModoLevel],
    ) -> Optional[QuasiModoLevel]:
        if not qmh_levels:
            return None
        
        valid_qmhs = [qmh for qmh in qmh_levels if qmh.is_valid]
        
        if not valid_qmhs:
            return None
        
        return max(valid_qmhs, key=lambda x: x.timestamp)
