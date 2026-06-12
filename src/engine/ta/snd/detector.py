from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.candles import CandleAnalyzer
from engine.ta.common.analyzers.swings import SwingAnalyzer
from engine.ta.common.analyzers.marubozu import MarubozuAnalyzer
from engine.ta.common.analyzers.compression import CompressionAnalyzer
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.constants import Direction
from engine.ta.models.candle import CandleSequence
from engine.ta.models.candidate import SnDCandidate
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.snd.config import SnDConfig
from engine.ta.snd.detectors.qm import QMDetector
from engine.ta.snd.detectors.sr_flip import SRFlipDetector
from engine.ta.snd.detectors.rs_flip import RSFlipDetector
from engine.ta.snd.detectors.previous_levels import PreviousLevelDetector
from engine.ta.snd.detectors.mpl import MPLDetector
from engine.ta.snd.detectors.fakeouts import FakeoutDetector
from engine.ta.snd.detectors.supply_demand import SupplyDemandDetector
from engine.ta.snd.validators.marubozu.validator import MarubozuValidator
from engine.ta.snd.validators.ltf.confirmation import LTFConfirmationValidator
from engine.ta.snd.builders.candidates.fakeout import FakeoutCandidateBuilder
from engine.ta.snd.builders.candidates.qm import QMCandidateBuilder
from engine.ta.snd.builders.candidates.continuation import ContinuationCandidateBuilder

logger = get_logger(__name__)


class SnDDetector:
    """
    SnD orchestration entrypoint.

    Coordinates all SnD pattern detection:
    1. Runs all SnD detectors (QM, SR/RS Flip, Previous Levels, MPL, Fakeouts)
    2. Extracts Supply/Demand zones
    3. Validates Marubozu quality (non-negotiable)
    4. Validates LTF confirmations (4 requirements)
    5. Builds candidates using fakeout/QM/continuation builders
    6. Outputs SnDCandidate models for processor

    Enforces all 9 Universal Rules:
    1. Marubozu is non-negotiable
    2. Minimum 2 Previous Highs/Lows
    3. Entry is a zone, not a line
    4. Top-down timeframe execution (H4/D1 → H1/M30 → M15/M5 → M1)
    5. Compression adds conviction
    6. Diamond Fakeout is exhaustion warning
    7. Fakeout broken by Marubozu = entry imminent
    8. Multiple fakeout tests = trend strength
    9. Fibonacci confluence = 90% probability
    """

    def __init__(
        self,
        config: SnDConfig,
        candle_analyzer: CandleAnalyzer,
        swing_analyzer: SwingAnalyzer,
        marubozu_analyzer: MarubozuAnalyzer,
        compression_analyzer: CompressionAnalyzer,
        fibonacci_analyzer: FibonacciAnalyzer,
    ) -> None:
        self.config = config
        self.candle_analyzer = candle_analyzer
        self.swing_analyzer = swing_analyzer
        self.marubozu_analyzer = marubozu_analyzer
        self.compression_analyzer = compression_analyzer
        self.fibonacci_analyzer = fibonacci_analyzer

        self.qm_detector = QMDetector(config)
        self.sr_flip_detector = SRFlipDetector(config, marubozu_analyzer)
        self.rs_flip_detector = RSFlipDetector(config, marubozu_analyzer)
        self.previous_level_detector = PreviousLevelDetector(config)
        self.mpl_detector = MPLDetector(config)
        self.fakeout_detector = FakeoutDetector(
            config, compression_analyzer, marubozu_analyzer
        )
        self.supply_demand_detector = SupplyDemandDetector(config)

        self.marubozu_validator = MarubozuValidator(config, marubozu_analyzer)
        self.ltf_validator = LTFConfirmationValidator(
            config, compression_analyzer, fibonacci_analyzer
        )

        self.fakeout_builder = FakeoutCandidateBuilder(
            config,
            self.marubozu_validator,
            self.ltf_validator,
            fibonacci_analyzer,
        )
        self.qm_builder = QMCandidateBuilder(
            config,
            self.marubozu_validator,
            self.ltf_validator,
            fibonacci_analyzer,
        )
        self.continuation_builder = ContinuationCandidateBuilder(
            config,
            self.marubozu_validator,
            self.ltf_validator,
            fibonacci_analyzer,
        )

        self._logger = get_logger(__name__)

    def detect_patterns(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
    ) -> list[SnDCandidate]:
        """
        Main orchestration method - detects all SnD patterns and builds candidates.

        Top-down execution (Universal Rule 4):
        1. HTF (H4/D1): Identify QM structure, QML/QMH, Previous Highs/Lows
        2. Mid TF (H1/M30): Confirm SR/RS Flip zone, fakeout formation
        3. Lower TF (M15/M5): Confirm Compression inside fakeout zone
        4. Lowest TF (M1): Find Decision Point - exact rejection candle
        """
        if not self.config.enabled:
            return []

        self._logger.info(
            "snd_detection_started",
            extra={
                "symbol": htf_sequence.symbol,
                "htf_timeframe": htf_sequence.timeframe,
                "ltf_timeframe": ltf_sequence.timeframe,
            },
        )

        htf_swing_highs = self.swing_analyzer.detect_swing_highs(htf_sequence)
        htf_swing_lows = self.swing_analyzer.detect_swing_lows(htf_sequence)

        htf_qml_levels = self.qm_detector.detect_qml(
            htf_sequence, htf_swing_highs, htf_swing_lows
        )
        htf_qmh_levels = self.qm_detector.detect_qmh(
            htf_sequence, htf_swing_lows, htf_swing_highs
        )

        htf_previous_highs = self.previous_level_detector.detect_previous_highs(
            htf_sequence,
            htf_swing_highs,
        )
        htf_previous_lows = self.previous_level_detector.detect_previous_lows(
            htf_sequence,
            htf_swing_lows,
        )

        ltf_swing_highs = self.swing_analyzer.detect_swing_highs(ltf_sequence)
        ltf_swing_lows = self.swing_analyzer.detect_swing_lows(ltf_sequence)

        ltf_sr_flips = self.sr_flip_detector.detect_sr_flips(
            ltf_sequence, ltf_swing_lows
        )
        ltf_rs_flips = self.rs_flip_detector.detect_rs_flips(
            ltf_sequence, ltf_swing_highs
        )

        retracement = self._create_fibonacci_retracement(
            htf_swing_highs,
            htf_swing_lows,
        )

        candidates = []

        # Build QML-based candidates (bearish setups)
        for qml in htf_qml_levels:
            matching_previous_highs = (
                self.previous_level_detector.find_previous_highs_at_qml(
                    htf_previous_highs,
                    qml.level,
                    htf_sequence.symbol,
                )
            )

            for sr_flip in ltf_sr_flips:
                fakeout_tests = self.fakeout_detector.detect_resistance_fakeouts(
                    ltf_sequence,
                    sr_flip.new_resistance_level,
                    sr_flip.breakout_candle_index,
                )

                if not fakeout_tests:
                    continue

                breakout_candle_index = (
                    self.fakeout_detector.check_fakeout_broken_by_marubozu(
                        ltf_sequence,
                        sr_flip.new_resistance_level,
                        Direction.BEARISH,
                        fakeout_tests[-1].candle_index,
                    )
                )

                mpl_levels = self.mpl_detector.detect_bearish_mpl(
                    htf_sequence,
                    qml.level,
                    qml.hh_index if hasattr(qml, "hh_index") else 0,
                )

                if self.config.enable_qml_baseline:
                    candidate = self.qm_builder.build_qml_baseline_short(
                        htf_sequence,
                        ltf_sequence,
                        qml,
                        sr_flip.new_resistance_level,
                        fakeout_tests,
                        breakout_candle_index,
                        retracement,
                    )
                    if candidate:
                        candidates.append(candidate)

                if (
                    self.config.enable_qml_previous_levels_type1
                    or self.config.enable_qml_previous_levels_type2
                ):
                    for prev_high in matching_previous_highs:
                        mpl = mpl_levels[0] if mpl_levels else None

                        candidate = self.qm_builder.build_qml_killer_setup_short(
                            htf_sequence,
                            ltf_sequence,
                            qml,
                            sr_flip.new_resistance_level,
                            fakeout_tests,
                            breakout_candle_index,
                            prev_high,
                            mpl,
                            retracement,
                        )
                        if candidate:
                            candidates.append(candidate)

                if self.config.enable_fakeout_king:
                    for prev_high in matching_previous_highs:
                        candidate = self.fakeout_builder.build_fakeout_king_short(
                            htf_sequence,
                            ltf_sequence,
                            sr_flip.new_resistance_level,
                            fakeout_tests,
                            breakout_candle_index,
                            prev_high,
                            retracement,
                        )
                        if candidate:
                            candidates.append(candidate)

                # Build continuation candidates (bearish)
                # Requires 2+ fakeout tests + previous highs (stricter)
                if matching_previous_highs and len(fakeout_tests) >= 2:
                    for prev_high in matching_previous_highs:
                        candidate = self.continuation_builder.build_continuation_short(
                            htf_sequence,
                            ltf_sequence,
                            qml,
                            sr_flip.new_resistance_level,
                            fakeout_tests,
                            breakout_candle_index,
                            prev_high,
                            retracement,
                        )
                        if candidate:
                            candidates.append(candidate)

        # Build QMH-based candidates (bullish setups)
        for qmh in htf_qmh_levels:
            matching_previous_lows = (
                self.previous_level_detector.find_previous_lows_at_qmh(
                    htf_previous_lows,
                    qmh.level,
                    htf_sequence.symbol,
                )
            )

            for rs_flip in ltf_rs_flips:
                fakeout_tests = self.fakeout_detector.detect_support_fakeouts(
                    ltf_sequence,
                    rs_flip.new_support_level,
                    rs_flip.breakout_candle_index,
                )

                if not fakeout_tests:
                    continue

                breakout_candle_index = (
                    self.fakeout_detector.check_fakeout_broken_by_marubozu(
                        ltf_sequence,
                        rs_flip.new_support_level,
                        Direction.BULLISH,
                        fakeout_tests[-1].candle_index,
                    )
                )

                mpl_levels = self.mpl_detector.detect_bullish_mpl(
                    htf_sequence,
                    qmh.level,
                    qmh.ll_index if hasattr(qmh, "ll_index") else 0,
                )

                if self.config.enable_qml_baseline:
                    candidate = self.qm_builder.build_qmh_baseline_long(
                        htf_sequence,
                        ltf_sequence,
                        qmh,
                        rs_flip.new_support_level,
                        fakeout_tests,
                        breakout_candle_index,
                        retracement,
                    )
                    if candidate:
                        candidates.append(candidate)

                if (
                    self.config.enable_qml_previous_levels_type1
                    or self.config.enable_qml_previous_levels_type2
                ):
                    for prev_low in matching_previous_lows:
                        mpl = mpl_levels[0] if mpl_levels else None

                        candidate = self.qm_builder.build_qmh_killer_setup_long(
                            htf_sequence,
                            ltf_sequence,
                            qmh,
                            rs_flip.new_support_level,
                            fakeout_tests,
                            breakout_candle_index,
                            prev_low,
                            mpl,
                            retracement,
                        )
                        if candidate:
                            candidates.append(candidate)

                if self.config.enable_fakeout_king:
                    for prev_low in matching_previous_lows:
                        candidate = self.fakeout_builder.build_fakeout_king_long(
                            htf_sequence,
                            ltf_sequence,
                            rs_flip.new_support_level,
                            fakeout_tests,
                            breakout_candle_index,
                            prev_low,
                            retracement,
                        )
                        if candidate:
                            candidates.append(candidate)

                # Build continuation candidates (bullish)
                if matching_previous_lows and len(fakeout_tests) >= 2:
                    for prev_low in matching_previous_lows:
                        candidate = self.continuation_builder.build_continuation_long(
                            htf_sequence,
                            ltf_sequence,
                            qmh,
                            rs_flip.new_support_level,
                            fakeout_tests,
                            breakout_candle_index,
                            prev_low,
                            retracement,
                        )
                        if candidate:
                            candidates.append(candidate)

        # Select the best candidate per direction per timeframe.
        # The LLM needs the highest-quality setup, not dozens of
        # near-duplicates at slightly different QM price levels
        # with the same fakeout/flip data.
        filtered = self._select_best_per_direction(candidates)

        self._logger.info(
            "snd_detection_completed",
            extra={
                "symbol": htf_sequence.symbol,
                "total_candidates_raw": len(candidates),
                "total_candidates_filtered": len(filtered),
                "htf_qml_count": len(htf_qml_levels),
                "htf_qmh_count": len(htf_qmh_levels),
                "ltf_sr_flips": len(ltf_sr_flips),
                "ltf_rs_flips": len(ltf_rs_flips),
            },
        )

        return filtered

    @staticmethod
    def _select_best_per_direction(
        candidates: list[SnDCandidate],
    ) -> list[SnDCandidate]:
        """Keep only the highest-confluence candidate per direction per timeframe.

        Groups candidates by (timeframe, direction) and selects the one
        with the highest confluence count.  On ties, the most recent
        candidate (by timestamp) wins.

        This reduces e.g. 68 near-duplicate QML/QMH candidates down to
        at most 2 per timeframe pair (1 bullish, 1 bearish).
        """
        best: dict[tuple[str, str], SnDCandidate] = {}

        for candidate in candidates:
            key = (str(candidate.timeframe), str(candidate.direction))
            confluences = (
                candidate.metadata.get("confluences", 0) if candidate.metadata else 0
            )

            existing = best.get(key)
            if existing is None:
                best[key] = candidate
                continue

            existing_confluences = (
                existing.metadata.get("confluences", 0) if existing.metadata else 0
            )

            # Higher confluence wins; on tie, more recent wins
            if confluences > existing_confluences:
                best[key] = candidate
            elif (
                confluences == existing_confluences
                and candidate.timestamp > existing.timestamp
            ):
                best[key] = candidate

        return list(best.values())

    def _create_fibonacci_retracement(
        self,
        swing_highs: list[SwingHigh],
        swing_lows: list[SwingLow],
    ) -> Optional[FibonacciRetracement]:
        if not swing_highs or not swing_lows:
            return None

        latest_high = self.swing_analyzer.get_latest_swing_high(swing_highs)
        latest_low = self.swing_analyzer.get_latest_swing_low(swing_lows)

        if not latest_high or not latest_low:
            return None

        if latest_high.price <= latest_low.price:
            return None

        is_bullish = latest_low.timestamp > latest_high.timestamp

        return self.fibonacci_analyzer.create_retracement(
            latest_high,
            latest_low,
            is_bullish,
        )
