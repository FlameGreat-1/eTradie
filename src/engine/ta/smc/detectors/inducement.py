from engine.shared.logging import get_logger
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.liquidity_event import InducementEvent
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class InducementDetector:
    """
    Detects Inducement (IDM) events.
    
    Inducement is a false engineered move to trick traders into entering prematurely.
    It exists at swing highs/lows where stops are placed - mostly internal highs/lows.
    
    Universal Rule: Never enter at inducement - wait for it to be taken out first,
    then look for entry at the real POI (Order Block).
    
    Inducement Requirements:
    - Must be internal swing high/low (not major structure)
    - Must be taken out before price reaches the real entry zone
    - Traders who enter at inducement get wiped out before real move
    """
    
    def __init__(self, config: SMCConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)
    
    def detect_bullish_inducement(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
    ) -> list[InducementEvent]:
        inducement_events = []
        
        internal_lows = [sl for sl in swing_lows if sl.strength < 5]
        
        for i, internal_low in enumerate(internal_lows):
            if internal_low.index >= len(sequence.candles) - 1:
                continue
            
            cleared = False
            cleared_timestamp = None
            
            for j in range(internal_low.index + 1, len(sequence.candles)):
                candle = sequence.candles[j]
                
                if candle.low <= internal_low.price:
                    cleared = True
                    cleared_timestamp = candle.timestamp
                    break
            
            inducement = InducementEvent(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                timestamp=internal_low.timestamp,
                inducement_level=internal_low.price,
                inducement_timestamp=internal_low.timestamp,
                direction=Direction.BULLISH,
                cleared=cleared,
                cleared_timestamp=cleared_timestamp,
                candle_index=internal_low.index,
                is_internal=True,
            )
            
            inducement_events.append(inducement)
            
            if cleared:
                self._logger.debug(
                    "bullish_inducement_cleared",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "inducement_level": internal_low.price,
                        "cleared_timestamp": cleared_timestamp.isoformat() if cleared_timestamp else None,
                    },
                )
        
        return inducement_events
    
    def detect_bearish_inducement(
        self,
        sequence: CandleSequence,
        swing_highs: list[SwingHigh],
    ) -> list[InducementEvent]:
        inducement_events = []
        
        internal_highs = [sh for sh in swing_highs if sh.strength < 5]
        
        for i, internal_high in enumerate(internal_highs):
            if internal_high.index >= len(sequence.candles) - 1:
                continue
            
            cleared = False
            cleared_timestamp = None
            
            for j in range(internal_high.index + 1, len(sequence.candles)):
                candle = sequence.candles[j]
                
                if candle.high >= internal_high.price:
                    cleared = True
                    cleared_timestamp = candle.timestamp
                    break
            
            inducement = InducementEvent(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                timestamp=internal_high.timestamp,
                inducement_level=internal_high.price,
                inducement_timestamp=internal_high.timestamp,
                direction=Direction.BEARISH,
                cleared=cleared,
                cleared_timestamp=cleared_timestamp,
                candle_index=internal_high.index,
                is_internal=True,
            )
            
            inducement_events.append(inducement)
            
            if cleared:
                self._logger.debug(
                    "bearish_inducement_cleared",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe,
                        "inducement_level": internal_high.price,
                        "cleared_timestamp": cleared_timestamp.isoformat() if cleared_timestamp else None,
                    },
                )
        
        return inducement_events
    
    def get_cleared_inducements(
        self,
        inducement_events: list[InducementEvent],
    ) -> list[InducementEvent]:
        return [idm for idm in inducement_events if idm.cleared]
