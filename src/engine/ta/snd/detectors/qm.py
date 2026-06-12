from engine.shared.logging import get_logger
from engine.ta.constants import Direction, Timeframe
from engine.ta.models.candle import CandleSequence
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.models.zone import QuasiModoLevel
from engine.ta.snd.config import SnDConfig

logger = get_logger(__name__)


class QMDetector:
    """
    Detects Quasimodo (QM) structures and QML/QMH levels.

    QM Structure Definition:
    - Bearish QM (QML): H -> HH -> break of H level = QML established
    - Bullish QM (QMH): L -> LL -> break of L level = QMH established

    QML/QMH is the target level where Supply/Demand zones are located.
    All SnD patterns revolve around price reaching the QML/QMH.

    Requirements:
    - Must have clear 3-swing structure (H -> HH -> break OR L -> LL -> break)
    - Break must be substantial close beyond the level (Marubozu) OR confirmed via multi-candle closes
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
        swing_lows: list[SwingLow],
    ) -> list[QuasiModoLevel]:
        """Detect QML levels (bearish).

        QM structure: H -> L -> HH -> break of L level (Neckline) = QML established.
        QML sits at the first H price (the level where Supply zone sits).
        """
        qml_levels = []

        if len(swing_highs) < 2 or not swing_lows:
            return qml_levels

        sorted_highs = sorted(swing_highs, key=lambda x: x.timestamp)
        sorted_lows = sorted(swing_lows, key=lambda x: x.timestamp)
        required_closes = self._get_required_confirmations(sequence.timeframe)

        for i in range(len(sorted_highs) - 1):
            h = sorted_highs[i]  # H  (Left Shoulder)
            hh = sorted_highs[i + 1]  # HH (Head)

            # HH must be strictly higher than H
            if hh.price <= h.price:
                continue

            # Find the lowest L (Neckline) that occurred exactly between H and HH
            neckline_l: SwingLow | None = None
            lowest_price = float("inf")

            for l in sorted_lows:
                if h.timestamp < l.timestamp < hh.timestamp and l.price < lowest_price:
                    lowest_price = l.price
                    neckline_l = l

            # If no L exists between H and HH, it's not a valid QM structure
            if not neckline_l:
                continue

            # Look for a candle that closes below the Neckline (L)
            first_break_idx: int | None = None

            for j in range(hh.index + 1, len(sequence.candles)):
                candle = sequence.candles[j]
                if candle.close < neckline_l.price:
                    first_break_idx = j
                    break

            if first_break_idx is None:
                continue

            sequence.candles[first_break_idx]

            # Count consecutive candle closes below the Neckline level
            confirmed_count = 0
            for k in range(first_break_idx, len(sequence.candles)):
                if sequence.candles[k].close < neckline_l.price:
                    confirmed_count += 1
                else:
                    break

                if confirmed_count >= required_closes:
                    break

            if confirmed_count < required_closes:
                continue

            # QM confirmed
            confirm_candle_idx = first_break_idx + required_closes - 1
            if confirm_candle_idx >= len(sequence.candles):
                confirm_candle_idx = len(sequence.candles) - 1

            confirm_candle = sequence.candles[confirm_candle_idx]
            break_ts = confirm_candle.timestamp
            break_candle_idx = first_break_idx

            qml = QuasiModoLevel(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                qml_price=h.price,
                timestamp=h.timestamp,
                candle_index=break_candle_idx,
                direction=Direction.BEARISH,
                h_price=h.price,
                hh_price=hh.price,
                l_price=neckline_l.price,
                ll_price=confirm_candle.close,
                h_timestamp=h.timestamp,
                hh_timestamp=hh.timestamp,
                l_timestamp=neckline_l.timestamp,
                ll_timestamp=break_ts,
                hh_index=hh.index,
                break_timestamp=break_ts,
                is_valid=True,
            )

            qml_levels.append(qml)

            self._logger.debug(
                "qml_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe.value,
                    "qml_price": h.price,
                    "h_price": h.price,
                    "hh_price": hh.price,
                    "neckline_l": neckline_l.price,
                    "confirm_candles_required": required_closes,
                },
            )

        return qml_levels

    def detect_qmh(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
        swing_highs: list[SwingHigh],
    ) -> list[QuasiModoLevel]:
        """Detect QMH levels (bullish).

        QM structure: L -> H -> LL -> break of H level (Neckline) = QMH established.
        QMH sits at the first L price (the level where Demand zone sits).
        """
        qmh_levels = []

        if len(swing_lows) < 2 or not swing_highs:
            return qmh_levels

        sorted_lows = sorted(swing_lows, key=lambda x: x.timestamp)
        sorted_highs = sorted(swing_highs, key=lambda x: x.timestamp)
        required_closes = self._get_required_confirmations(sequence.timeframe)

        for i in range(len(sorted_lows) - 1):
            l = sorted_lows[i]  # L  (Left Shoulder)
            ll = sorted_lows[i + 1]  # LL (Head)

            # LL must be strictly lower than L
            if ll.price >= l.price:
                continue

            # Find the highest H (Neckline) that occurred exactly between L and LL
            neckline_h: SwingHigh | None = None
            highest_price = -float("inf")

            for h in sorted_highs:
                if l.timestamp < h.timestamp < ll.timestamp and h.price > highest_price:
                    highest_price = h.price
                    neckline_h = h

            # If no H exists between L and LL, it's not a valid QM structure
            if not neckline_h:
                continue

            # Look for a candle that closes above the Neckline (H)
            first_break_idx: int | None = None

            for j in range(ll.index + 1, len(sequence.candles)):
                candle = sequence.candles[j]
                if candle.close > neckline_h.price:
                    first_break_idx = j
                    break

            if first_break_idx is None:
                continue

            sequence.candles[first_break_idx]

            # Count consecutive candle closes above the Neckline level
            confirmed_count = 0
            for k in range(first_break_idx, len(sequence.candles)):
                if sequence.candles[k].close > neckline_h.price:
                    confirmed_count += 1
                else:
                    break

                if confirmed_count >= required_closes:
                    break

            if confirmed_count < required_closes:
                continue

            # QM confirmed
            confirm_candle_idx = first_break_idx + required_closes - 1
            if confirm_candle_idx >= len(sequence.candles):
                confirm_candle_idx = len(sequence.candles) - 1

            confirm_candle = sequence.candles[confirm_candle_idx]
            break_ts = confirm_candle.timestamp
            break_candle_idx = first_break_idx

            qmh = QuasiModoLevel(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                qml_price=l.price,
                timestamp=l.timestamp,
                candle_index=break_candle_idx,
                direction=Direction.BULLISH,
                l_price=l.price,
                ll_price=ll.price,
                h_price=neckline_h.price,
                hh_price=confirm_candle.close,
                l_timestamp=l.timestamp,
                ll_timestamp=ll.timestamp,
                h_timestamp=neckline_h.timestamp,
                hh_timestamp=break_ts,
                ll_index=ll.index,
                break_timestamp=break_ts,
                is_valid=True,
            )

            qmh_levels.append(qmh)

            self._logger.debug(
                "qmh_detected",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe.value,
                    "qmh_price": l.price,
                    "l_price": l.price,
                    "ll_price": ll.price,
                    "neckline_h": neckline_h.price,
                    "confirm_candles_required": required_closes,
                },
            )

        return qmh_levels

    @staticmethod
    def get_latest_qml(
        qml_levels: list[QuasiModoLevel],
    ) -> QuasiModoLevel | None:
        if not qml_levels:
            return None

        valid_qmls = [qml for qml in qml_levels if qml.is_valid]

        if not valid_qmls:
            return None

        return max(valid_qmls, key=lambda x: x.timestamp)

    @staticmethod
    def get_latest_qmh(
        qmh_levels: list[QuasiModoLevel],
    ) -> QuasiModoLevel | None:
        if not qmh_levels:
            return None

        valid_qmhs = [qmh for qmh in qmh_levels if qmh.is_valid]

        if not valid_qmhs:
            return None

        return max(valid_qmhs, key=lambda x: x.timestamp)

    @staticmethod
    def _get_required_confirmations(timeframe: Timeframe) -> int:
        """
        Dynamically scale the required candle closes for QM structural breaks
        based on the timeframe. Higher timeframes require more closes to
        prevent getting faked out by a single wicky candle.
        """
        if timeframe in [Timeframe.M1, Timeframe.M5]:
            return 1
        if timeframe in [Timeframe.M15, Timeframe.M30]:
            return 2
        return 3
