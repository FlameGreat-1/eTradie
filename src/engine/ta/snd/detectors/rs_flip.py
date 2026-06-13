from engine.shared.logging import get_logger
from engine.ta.common.analyzers.marubozu import MarubozuAnalyzer
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.structure_event import RSFlip
from engine.ta.models.swing import SwingHigh
from engine.ta.snd.config import SnDConfig

logger = get_logger(__name__)


class RSFlipDetector:
    """
    Detects Resistance-to-Support Flip (RS Flip) structures.

    RS Flip Formation (Universal Rule 1):
    - Resistance level exists (swing high)
    - Single bullish Marubozu breaks Resistance upward
    - RS Flip zone created (old Resistance is now Support)
    - Price retraces down to RS Flip zone
    - Fakeouts form at zone (S1, S2, S3, S4)
    - Entry in Demand zone between RS Flip and QMH

    Requirements:
    - Marubozu is non-negotiable (full body, minimal wicks)
    - Must be substantial close above the level
    - Creates the top boundary of Demand zone
    """

    def __init__(
        self,
        config: SnDConfig,
        marubozu_analyzer: MarubozuAnalyzer,
    ) -> None:
        self.config = config
        self.marubozu_analyzer = marubozu_analyzer
        self._logger = get_logger(__name__)

    def detect_rs_flips(
        self,
        sequence: CandleSequence,
        swing_highs: list[SwingHigh],
    ) -> list[RSFlip]:
        """Detect RS Flip events.

        For each swing high (Resistance level), look for a bullish Marubozu
        that closes above it. That Marubozu breaks Resistance -> the level
        flips to Support.

        Uses timeframe-aware Marubozu detection so that LTF candles
        are not held to the same absolute pip displacement as HTF.
        """
        rs_flips = []

        for swing_high in swing_highs:
            if swing_high.index >= len(sequence.candles) - 1:
                continue

            for i in range(swing_high.index + 1, len(sequence.candles)):
                candle = sequence.candles[i]

                if not self.marubozu_analyzer.is_bullish_marubozu_for_timeframe(candle, sequence.timeframe):
                    continue

                if candle.close <= swing_high.price:
                    continue

                rs_flip = RSFlip(
                    symbol=sequence.symbol,
                    timeframe=sequence.timeframe,
                    timestamp=candle.timestamp,
                    original_resistance_level=swing_high.price,
                    original_resistance_timestamp=swing_high.timestamp,
                    breakout_candle_index=i,
                    breakout_price=candle.close,
                    new_support_level=swing_high.price,
                    direction=Direction.BULLISH,
                    is_valid=True,
                )

                rs_flips.append(rs_flip)

                self._logger.debug(
                    "rs_flip_detected",
                    extra={
                        "symbol": sequence.symbol,
                        "timeframe": sequence.timeframe.value,
                        "flip_level": swing_high.price,
                        "breakout_price": candle.close,
                    },
                )

                break

        return rs_flips

    @staticmethod
    def get_latest_rs_flip(
        rs_flips: list[RSFlip],
    ) -> RSFlip | None:
        if not rs_flips:
            return None

        valid_flips = [flip for flip in rs_flips if flip.is_valid]

        if not valid_flips:
            return None

        return max(valid_flips, key=lambda x: x.timestamp)

    def validate_rs_flip_with_marubozu(
        self,
        rs_flip: RSFlip,
        sequence: CandleSequence,
    ) -> bool:
        if rs_flip.breakout_candle_index >= len(sequence.candles):
            return False

        breakout_candle = sequence.candles[rs_flip.breakout_candle_index]

        return self.marubozu_analyzer.is_bullish_marubozu_for_timeframe(breakout_candle, sequence.timeframe)
