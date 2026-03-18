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
    - Bearish QM (QML): H -> HH -> break of H level = QML established
    - Bullish QM (QMH): L -> LL -> break of L level = QMH established

    QML/QMH is the target level where Supply/Demand zones are located.
    All SnD patterns revolve around price reaching the QML/QMH.

    Requirements:
    - Must have clear 3-swing structure (H -> HH -> break OR L -> LL -> break)
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
        """Detect QML levels (bearish).

        QM structure: H -> HH -> break of H level = QML established.
        QML sits at the first H price (the level where Supply zone sits).
        """
        qml_levels = []

        if len(swing_highs) < 2:
            return qml_levels

        sorted_highs = sorted(swing_highs, key=lambda x: x.timestamp)

        for i in range(len(sorted_highs) - 1):
            h = sorted_highs[i]       # H  (first high)
            hh = sorted_highs[i + 1]  # HH (higher high)

            # HH must be higher than H
            if hh.price <= h.price:
                continue

            # Look for a candle that closes below H (the break)
            break_detected = False
            break_candle_idx = None
            break_ts = None

            for j in range(hh.index + 1, len(sequence.candles)):
                candle = sequence.candles[j]

                if candle.close < h.price:
                    break_detected = True
                    break_candle_idx = j
                    break_ts = candle.timestamp
                    break

            if not break_detected:
                continue

            qml = QuasiModoLevel(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                qml_price=h.price,
                timestamp=h.timestamp,
                candle_index=break_candle_idx,
                direction=Direction.BEARISH,
                h_price=h.price,
                hh_price=hh.price,
                h_timestamp=h.timestamp,
                hh_timestamp=hh.timestamp,
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
                },
            )

        return qml_levels

    def detect_qmh(
        self,
        sequence: CandleSequence,
        swing_lows: list[SwingLow],
    ) -> list[QuasiModoLevel]:
        """Detect QMH levels (bullish).

        QM structure: L -> LL -> break of L level = QMH established.
        QMH sits at the first L price (the level where Demand zone sits).
        """
        qmh_levels = []

        if len(swing_lows) < 2:
            return qmh_levels

        sorted_lows = sorted(swing_lows, key=lambda x: x.timestamp)

        for i in range(len(sorted_lows) - 1):
            l = sorted_lows[i]       # L  (first low)
            ll = sorted_lows[i + 1]  # LL (lower low)

            # LL must be lower than L
            if ll.price >= l.price:
                continue

            # Look for a candle that closes above L (the break)
            break_detected = False
            break_candle_idx = None
            break_ts = None

            for j in range(ll.index + 1, len(sequence.candles)):
                candle = sequence.candles[j]

                if candle.close > l.price:
                    break_detected = True
                    break_candle_idx = j
                    break_ts = candle.timestamp
                    break

            if not break_detected:
                continue

            qmh = QuasiModoLevel(
                symbol=sequence.symbol,
                timeframe=sequence.timeframe,
                qml_price=l.price,
                timestamp=l.timestamp,
                candle_index=break_candle_idx,
                direction=Direction.BULLISH,
                l_price=l.price,
                ll_price=ll.price,
                l_timestamp=l.timestamp,
                ll_timestamp=ll.timestamp,
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
                },
            )

        return qmh_levels

    @staticmethod
    def get_latest_qml(
        qml_levels: list[QuasiModoLevel],
    ) -> Optional[QuasiModoLevel]:
        if not qml_levels:
            return None

        valid_qmls = [qml for qml in qml_levels if qml.is_valid]

        if not valid_qmls:
            return None

        return max(valid_qmls, key=lambda x: x.timestamp)

    @staticmethod
    def get_latest_qmh(
        qmh_levels: list[QuasiModoLevel],
    ) -> Optional[QuasiModoLevel]:
        if not qmh_levels:
            return None

        valid_qmhs = [qmh for qmh in qmh_levels if qmh.is_valid]

        if not valid_qmhs:
            return None

        return max(valid_qmhs, key=lambda x: x.timestamp)
