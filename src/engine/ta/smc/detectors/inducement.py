from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.liquidity_event import InducementEvent
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class InducementDetector:
    """
    Detects Inducement (IDM) events.

    Inducement is a false engineered move to trick traders into entering
    prematurely.  It exists at internal swing highs/lows where stops are
    placed.

    Universal Rule (SMC-LIQ-004): Never enter at inducement — wait for it
    to be taken out first, then look for entry at the real POI (Order
    Block).

    Inducement Clearance (SMC-MS-003 / SMC-MS-004):
    - A liquidity grab requires a wick that penetrates beyond the level
      by a meaningful margin, activating the stops resting there.
    - A trivial retest that only touches the level (equal price) does
      NOT clear the inducement — stops are triggered by penetration,
      not by tagging.
    - The minimum penetration is configurable via
      ``SMCConfig.inducement_min_break_pips`` (default 1.0 pip) and is
      scaled per-symbol via ``get_pip_value`` so the same value works
      for FX, metals, indices, and crypto instruments.
    """

    def __init__(self, config: SMCConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)

    def detect_bullish_inducement(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
    ) -> list[InducementEvent]:
        inducement_events: list[InducementEvent] = []

        internal_lows = [sl for sl in swing_lows if sl.strength < 5]

        pip_value = float(get_pip_value(sequence.symbol))
        min_break = self.config.inducement_min_break_pips * pip_value

        for internal_low in internal_lows:
            if internal_low.index >= len(sequence.candles) - 1:
                continue

            # A bullish inducement (SSL resting below an internal low) is
            # swept only when a later candle's wick penetrates strictly
            # below the level by at least ``min_break`` pips.  Equal
            # touches and re-tests at the level do NOT clear it.
            clearance_threshold = internal_low.price - min_break

            cleared = False
            cleared_timestamp = None

            for j in range(internal_low.index + 1, len(sequence.candles)):
                candle = sequence.candles[j]
                if candle.low < clearance_threshold:
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
                        "clearance_threshold": clearance_threshold,
                        "min_break_pips": self.config.inducement_min_break_pips,
                        "cleared_timestamp": (
                            cleared_timestamp.isoformat() if cleared_timestamp else None
                        ),
                    },
                )

        return inducement_events

    def detect_bearish_inducement(
        self,
        sequence: CandleSequence,
        swing_highs: list[SwingHigh],
    ) -> list[InducementEvent]:
        inducement_events: list[InducementEvent] = []

        internal_highs = [sh for sh in swing_highs if sh.strength < 5]

        pip_value = float(get_pip_value(sequence.symbol))
        min_break = self.config.inducement_min_break_pips * pip_value

        for internal_high in internal_highs:
            if internal_high.index >= len(sequence.candles) - 1:
                continue

            # A bearish inducement (BSL resting above an internal high)
            # is swept only when a later candle's wick penetrates
            # strictly above the level by at least ``min_break`` pips.
            clearance_threshold = internal_high.price + min_break

            cleared = False
            cleared_timestamp = None

            for j in range(internal_high.index + 1, len(sequence.candles)):
                candle = sequence.candles[j]
                if candle.high > clearance_threshold:
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
                        "clearance_threshold": clearance_threshold,
                        "min_break_pips": self.config.inducement_min_break_pips,
                        "cleared_timestamp": (
                            cleared_timestamp.isoformat() if cleared_timestamp else None
                        ),
                    },
                )

        return inducement_events

    def get_cleared_inducements(
        self,
        inducement_events: list[InducementEvent],
    ) -> list[InducementEvent]:
        return [idm for idm in inducement_events if idm.cleared]
