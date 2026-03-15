"""
TA workflow orchestration — multi-timeframe top-down analysis.

The TAOrchestrator owns the analysis logic. It reads its own TAConfig
to determine which timeframes to analyze and runs a complete top-down
sweep from the highest configured timeframe to the lowest:

    W1 → D1 → H4 → H1  (pattern detection on each HTF pair)
    M30 → M15 → M5 → M1 (confirmation detection on each LTF pair)

The Gateway does NOT dictate timeframes. It simply calls:
    await orchestrator.analyze(symbol="EURUSD", lookback_periods=500)

and receives a fully structured multi-timeframe result.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from typing import Optional

from engine.config import TAConfig, get_ta_config
from engine.shared.logging import get_logger
from engine.ta.broker.base import BrokerBase
from engine.ta.common.services.alignment.service import AlignmentService
from engine.ta.common.services.snapshot.builder import SnapshotBuilder
from engine.ta.common.timeframe.manager import TimeframeManager
from engine.ta.constants import TIMEFRAME_MINUTES, Direction, Timeframe
from engine.ta.models.candle import CandleSequence
from engine.ta.models.candidate import SMCCandidate, SnDCandidate
from engine.ta.models.snapshot import MultiTimeframeSnapshot, TechnicalSnapshot
from engine.ta.smc.detector import SMCDetector
from engine.ta.snd.detector import SnDDetector
from engine.ta.storage.repositories.candle import CandleRepository
from engine.ta.storage.repositories.candidate import CandidateRepository
from engine.ta.storage.repositories.snapshot import SnapshotRepository

logger = get_logger(__name__)


class TAOrchestrator:
    """
    Multi-timeframe TA workflow orchestration.

    Coordinates a complete top-down analysis cycle for a single symbol:

    1. Fetch candles for every configured timeframe (HTF + LTF).
    2. Build a TechnicalSnapshot per timeframe via SnapshotBuilder.
    3. Run SMC detection on every adjacent HTF pair.
    4. Run SnD detection on every adjacent HTF pair.
    5. Run SMC/SnD confirmation on every adjacent LTF pair.
    6. Align all snapshots via AlignmentService.
    7. Persist every per-timeframe snapshot and all candidates.
    8. Return a structured multi-timeframe result dict.

    The orchestrator reads timeframe lists from TAConfig — it never
    hardcodes which timeframes to analyze.
    """

    def __init__(
        self,
        broker_client: BrokerBase,
        candle_repository: CandleRepository,
        snapshot_repository: SnapshotRepository,
        candidate_repository: CandidateRepository,
        smc_detector: SMCDetector,
        snd_detector: SnDDetector,
        snapshot_builder: SnapshotBuilder,
        alignment_service: AlignmentService,
        timeframe_manager: TimeframeManager,
        ta_config: Optional[TAConfig] = None,
    ) -> None:
        self.broker_client = broker_client
        self.candle_repository = candle_repository
        self.snapshot_repository = snapshot_repository
        self.candidate_repository = candidate_repository
        self.smc_detector = smc_detector
        self.snd_detector = snd_detector
        self.snapshot_builder = snapshot_builder
        self.alignment_service = alignment_service
        self.timeframe_manager = timeframe_manager
        self._config = ta_config or get_ta_config()
        self._logger = get_logger(__name__)

    # ── Public API ───────────────────────────────────────────────────

    async def analyze(
        self,
        symbol: str,
        lookback_periods: int = 500,
    ) -> dict:
        """
        Run a complete multi-timeframe top-down analysis for *symbol*.

        The method reads ``htf_timeframes`` and ``ltf_timeframes`` from
        TAConfig and iterates every configured timeframe from highest to
        lowest.  The caller does NOT specify timeframes — the TA engine
        owns that decision.

        Returns a structured dict consumed by the Gateway's TACollector:
        {
            "status": "success" | "insufficient_data" | "error",
            "symbol": "EURUSD",
            "htf_timeframes": ["D1", "H4", "H1"],
            "ltf_timeframes": ["M30", "M15", "M5", "M1"],
            "snapshots": { "D1": {…}, "H4": {…}, … },
            "smc_candidates": [ … ],
            "snd_candidates": [ … ],
            "smc_candidates_count": 5,
            "snd_candidates_count": 3,
            "alignment": { "D1_H4": {…}, "H4_H1": {…}, … },
            "overall_trend": "BULLISH" | "BEARISH" | "NEUTRAL",
            "error": null,
        }
        """
        htf_timeframes = sorted(
            self._config.htf_timeframes,
            key=lambda tf: TIMEFRAME_MINUTES[tf],
            reverse=True,
        )
        ltf_timeframes = sorted(
            self._config.ltf_timeframes,
            key=lambda tf: TIMEFRAME_MINUTES[tf],
            reverse=True,
        )
        all_timeframes = htf_timeframes + ltf_timeframes

        self._logger.info(
            "ta_mtf_analysis_started",
            extra={
                "symbol": symbol,
                "htf_timeframes": [tf.value for tf in htf_timeframes],
                "ltf_timeframes": [tf.value for tf in ltf_timeframes],
                "lookback_periods": lookback_periods,
            },
        )

        try:
            # ── Phase 1: Fetch candles for every timeframe ───────────
            sequences: dict[Timeframe, CandleSequence] = {}
            for tf in all_timeframes:
                seq = await self._fetch_sequence(symbol, tf, lookback_periods)
                if seq is not None:
                    sequences[tf] = seq

            if not sequences:
                self._logger.warning(
                    "ta_mtf_analysis_no_data",
                    extra={"symbol": symbol},
                )
                return self._build_result(
                    symbol=symbol,
                    status="insufficient_data",
                    htf_timeframes=htf_timeframes,
                    ltf_timeframes=ltf_timeframes,
                )

            # ── Phase 2: Build snapshot per timeframe ────────────────
            snapshots: dict[Timeframe, TechnicalSnapshot] = {}
            for tf, seq in sequences.items():
                snapshot = self._build_snapshot_for_timeframe(seq)
                if snapshot is not None:
                    snapshots[tf] = snapshot

            if not snapshots:
                self._logger.warning(
                    "ta_mtf_analysis_no_snapshots",
                    extra={"symbol": symbol},
                )
                return self._build_result(
                    symbol=symbol,
                    status="insufficient_data",
                    htf_timeframes=htf_timeframes,
                    ltf_timeframes=ltf_timeframes,
                )

            # ── Phase 3: Run pattern detection on HTF pairs ──────────
            all_smc: list[SMCCandidate] = []
            all_snd: list[SnDCandidate] = []

            available_htfs = [
                tf for tf in htf_timeframes if tf in sequences
            ]
            for i in range(len(available_htfs) - 1):
                higher_tf = available_htfs[i]
                lower_tf = available_htfs[i + 1]
                smc = self._run_smc_detection(
                    sequences[higher_tf], sequences[lower_tf],
                )
                snd = self._run_snd_detection(
                    sequences[higher_tf], sequences[lower_tf],
                )
                all_smc.extend(smc)
                all_snd.extend(snd)

            # ── Phase 4: Run confirmation detection on LTF pairs ─────
            available_ltfs = [
                tf for tf in ltf_timeframes if tf in sequences
            ]
            for i in range(len(available_ltfs) - 1):
                higher_tf = available_ltfs[i]
                lower_tf = available_ltfs[i + 1]
                smc = self._run_smc_detection(
                    sequences[higher_tf], sequences[lower_tf],
                )
                snd = self._run_snd_detection(
                    sequences[higher_tf], sequences[lower_tf],
                )
                all_smc.extend(smc)
                all_snd.extend(snd)

            # ── Phase 5: Cross-boundary pair (lowest HTF ↔ highest LTF)
            if available_htfs and available_ltfs:
                lowest_htf = available_htfs[-1]
                highest_ltf = available_ltfs[0]
                if (
                    lowest_htf in sequences
                    and highest_ltf in sequences
                    and self.timeframe_manager.is_htf_of(lowest_htf, highest_ltf)
                ):
                    smc = self._run_smc_detection(
                        sequences[lowest_htf], sequences[highest_ltf],
                    )
                    snd = self._run_snd_detection(
                        sequences[lowest_htf], sequences[highest_ltf],
                    )
                    all_smc.extend(smc)
                    all_snd.extend(snd)

            # ── Phase 6: Align adjacent snapshots ────────────────────
            alignments: dict[str, dict] = {}
            ordered_tfs = [tf for tf in all_timeframes if tf in snapshots]
            for i in range(len(ordered_tfs) - 1):
                higher_tf = ordered_tfs[i]
                lower_tf = ordered_tfs[i + 1]
                alignment_key = f"{higher_tf.value}_{lower_tf.value}"
                mtf_snap = self.alignment_service.check_alignment(
                    snapshots[higher_tf], snapshots[lower_tf],
                )
                alignments[alignment_key] = {
                    "htf_timeframe": higher_tf.value,
                    "ltf_timeframe": lower_tf.value,
                    "trends_aligned": mtf_snap.trends_aligned,
                    "htf_ltf_aligned": mtf_snap.htf_ltf_aligned,
                    "htf_trend": mtf_snap.htf_trend.value,
                    "ltf_trend": mtf_snap.ltf_trend.value,
                    "alignment_metadata": mtf_snap.alignment_metadata,
                }

            # ── Phase 7: Determine overall trend from highest TF ─────
            overall_trend = self._determine_overall_trend(
                snapshots, ordered_tfs,
            )

            # ── Phase 8: Persist all results ─────────────────────────
            await self._persist_all_results(
                snapshots, all_smc, all_snd,
            )

            self._logger.info(
                "ta_mtf_analysis_completed",
                extra={
                    "symbol": symbol,
                    "timeframes_analyzed": [tf.value for tf in ordered_tfs],
                    "snapshots_built": len(snapshots),
                    "smc_candidates": len(all_smc),
                    "snd_candidates": len(all_snd),
                    "alignments": len(alignments),
                    "overall_trend": overall_trend,
                },
            )

            return self._build_result(
                symbol=symbol,
                status="success",
                htf_timeframes=htf_timeframes,
                ltf_timeframes=ltf_timeframes,
                snapshots=snapshots,
                smc_candidates=all_smc,
                snd_candidates=all_snd,
                alignments=alignments,
                overall_trend=overall_trend,
            )

        except Exception as e:
            self._logger.error(
                "ta_mtf_analysis_failed",
                extra={
                    "symbol": symbol,
                    "error": str(e),
                },
                exc_info=True,
            )
            return self._build_result(
                symbol=symbol,
                status="error",
                htf_timeframes=htf_timeframes,
                ltf_timeframes=ltf_timeframes,
                error=str(e),
            )

    # ── Result builder ───────────────────────────────────────────────

    def _build_result(
        self,
        *,
        symbol: str,
        status: str,
        htf_timeframes: list[Timeframe],
        ltf_timeframes: list[Timeframe],
        snapshots: Optional[dict[Timeframe, TechnicalSnapshot]] = None,
        smc_candidates: Optional[list[SMCCandidate]] = None,
        snd_candidates: Optional[list[SnDCandidate]] = None,
        alignments: Optional[dict[str, dict]] = None,
        overall_trend: str = "NEUTRAL",
        error: Optional[str] = None,
    ) -> dict:
        """Build the structured result dict returned by analyze()."""
        smc_list = smc_candidates or []
        snd_list = snd_candidates or []
        snapshot_map = snapshots or {}

        serialized_snapshots: dict[str, dict] = {}
        for tf, snap in snapshot_map.items():
            serialized_snapshots[tf.value] = self._serialize_snapshot(snap)

        serialized_smc = [
            c.model_dump(mode="json") if hasattr(c, "model_dump") else {}
            for c in smc_list
        ]
        serialized_snd = [
            c.model_dump(mode="json") if hasattr(c, "model_dump") else {}
            for c in snd_list
        ]

        return {
            "status": status,
            "symbol": symbol,
            "htf_timeframes": [tf.value for tf in htf_timeframes],
            "ltf_timeframes": [tf.value for tf in ltf_timeframes],
            "snapshots": serialized_snapshots,
            "smc_candidates": serialized_smc,
            "snd_candidates": serialized_snd,
            "smc_candidates_count": len(smc_list),
            "snd_candidates_count": len(snd_list),
            "alignment": alignments or {},
            "overall_trend": overall_trend,
            "error": error,
        }

    # ── Candle fetching ──────────────────────────────────────────────

    async def _fetch_sequence(
        self,
        symbol: str,
        timeframe: Timeframe,
        lookback_periods: int,
    ) -> Optional[CandleSequence]:
        """Fetch candles for a single timeframe from store or broker."""
        end_time = datetime.now(UTC)
        start_time = self._calculate_start_time(
            end_time, timeframe, lookback_periods,
        )

        stored_candles = await self.candle_repository.find_by_time_range(
            symbol,
            timeframe.value,
            start_time,
            end_time,
        )

        if len(stored_candles) < lookback_periods * 0.8:
            self._logger.info(
                "fetching_candles_from_broker",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe.value,
                    "stored_count": len(stored_candles),
                    "required_count": lookback_periods,
                },
            )
            try:
                sequence = await self.broker_client.fetch_candles(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=start_time,
                    end_time=end_time,
                    count=lookback_periods,
                )
                if sequence and sequence.count > 0:
                    return sequence
            except Exception as e:
                self._logger.error(
                    "broker_fetch_failed",
                    extra={
                        "symbol": symbol,
                        "timeframe": timeframe.value,
                        "error": str(e),
                    },
                    exc_info=True,
                )

        if not stored_candles:
            self._logger.warning(
                "no_candle_data_available",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe.value,
                },
            )
            return None

        return CandleSequence(
            symbol=symbol,
            timeframe=timeframe,
            candles=stored_candles,
        )

    @staticmethod
    def _calculate_start_time(
        end_time: datetime,
        timeframe: Timeframe,
        lookback_periods: int,
    ) -> datetime:
        """Calculate start time using TIMEFRAME_MINUTES — no hardcoded branches."""
        minutes = TIMEFRAME_MINUTES.get(timeframe)
        if minutes is None:
            raise ValueError(f"Unknown timeframe: {timeframe}")
        return end_time - timedelta(minutes=minutes * lookback_periods)


    # ── Snapshot building ────────────────────────────────────────────

    def _build_snapshot_for_timeframe(
        self,
        sequence: CandleSequence,
    ) -> Optional[TechnicalSnapshot]:
        """Build a TechnicalSnapshot for a single timeframe's candle data."""
        try:
            snapshot = self.snapshot_builder.build_snapshot(candles=sequence)
            self._logger.debug(
                "snapshot_built_for_timeframe",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe.value,
                    "candle_count": sequence.count,
                    "swing_highs": len(snapshot.swing_highs),
                    "swing_lows": len(snapshot.swing_lows),
                    "trend_direction": snapshot.trend_direction.value,
                },
            )
            return snapshot
        except Exception as e:
            self._logger.error(
                "snapshot_build_failed",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe.value,
                    "error": str(e),
                },
                exc_info=True,
            )
            return None

    # ── Pattern detection ────────────────────────────────────────────

    def _run_smc_detection(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
    ) -> list[SMCCandidate]:
        """Run SMC pattern detection for one HTF/LTF pair."""
        self._logger.debug(
            "smc_detection_started",
            extra={
                "symbol": htf_sequence.symbol,
                "htf_timeframe": htf_sequence.timeframe.value,
                "ltf_timeframe": ltf_sequence.timeframe.value,
            },
        )
        try:
            candidates = self.smc_detector.detect_patterns(
                htf_sequence, ltf_sequence,
            )
            self._logger.debug(
                "smc_detection_completed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "htf_timeframe": htf_sequence.timeframe.value,
                    "ltf_timeframe": ltf_sequence.timeframe.value,
                    "candidates_count": len(candidates),
                },
            )
            return candidates
        except Exception as e:
            self._logger.error(
                "smc_detection_failed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "htf_timeframe": htf_sequence.timeframe.value,
                    "ltf_timeframe": ltf_sequence.timeframe.value,
                    "error": str(e),
                },
                exc_info=True,
            )
            return []

    def _run_snd_detection(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
    ) -> list[SnDCandidate]:
        """Run SnD pattern detection for one HTF/LTF pair."""
        self._logger.debug(
            "snd_detection_started",
            extra={
                "symbol": htf_sequence.symbol,
                "htf_timeframe": htf_sequence.timeframe.value,
                "ltf_timeframe": ltf_sequence.timeframe.value,
            },
        )
        try:
            candidates = self.snd_detector.detect_patterns(
                htf_sequence, ltf_sequence,
            )
            self._logger.debug(
                "snd_detection_completed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "htf_timeframe": htf_sequence.timeframe.value,
                    "ltf_timeframe": ltf_sequence.timeframe.value,
                    "candidates_count": len(candidates),
                },
            )
            return candidates
        except Exception as e:
            self._logger.error(
                "snd_detection_failed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "htf_timeframe": htf_sequence.timeframe.value,
                    "ltf_timeframe": ltf_sequence.timeframe.value,
                    "error": str(e),
                },
                exc_info=True,
            )
            return []

    # ── Overall trend ────────────────────────────────────────────────

    @staticmethod
    def _determine_overall_trend(
        snapshots: dict[Timeframe, TechnicalSnapshot],
        ordered_tfs: list[Timeframe],
    ) -> str:
        """
        Derive the overall market bias from the highest available timeframe.

        The highest timeframe's trend is the dominant bias. If it is
        NEUTRAL, we fall through to the next highest until we find a
        directional bias or exhaust all timeframes.
        """
        for tf in ordered_tfs:
            snap = snapshots.get(tf)
            if snap is None:
                continue
            if snap.trend_direction != Direction.NEUTRAL:
                return snap.trend_direction.value
        return Direction.NEUTRAL.value

    # ── Persistence ──────────────────────────────────────────────────

    async def _persist_all_results(
        self,
        snapshots: dict[Timeframe, TechnicalSnapshot],
        smc_candidates: list[SMCCandidate],
        snd_candidates: list[SnDCandidate],
    ) -> None:
        """Persist every per-timeframe snapshot and all candidates."""
        for tf, snapshot in snapshots.items():
            await self._persist_snapshot(snapshot)

        for candidate in smc_candidates:
            try:
                await self.candidate_repository.create_smc_candidate(candidate)
            except Exception as e:
                self._logger.error(
                    "smc_candidate_persistence_failed",
                    extra={
                        "symbol": candidate.symbol,
                        "pattern": candidate.pattern.value,
                        "error": str(e),
                    },
                    exc_info=True,
                )

        for candidate in snd_candidates:
            try:
                await self.candidate_repository.create_snd_candidate(candidate)
            except Exception as e:
                self._logger.error(
                    "snd_candidate_persistence_failed",
                    extra={
                        "symbol": candidate.symbol,
                        "pattern": candidate.pattern.value,
                        "error": str(e),
                    },
                    exc_info=True,
                )

        self._logger.debug(
            "persistence_completed",
            extra={
                "snapshots_persisted": len(snapshots),
                "smc_candidates_persisted": len(smc_candidates),
                "snd_candidates_persisted": len(snd_candidates),
            },
        )

    async def _persist_snapshot(self, snapshot: TechnicalSnapshot) -> None:
        """Persist a single TechnicalSnapshot to storage."""
        try:
            await self.snapshot_repository.create(
                symbol=snapshot.symbol,
                timeframe=snapshot.timeframe.value,
                timestamp=snapshot.timestamp,
                swing_highs=self._serialize_swing_highs(snapshot.swing_highs),
                swing_lows=self._serialize_swing_lows(snapshot.swing_lows),
                bms_events=self._serialize_bms_events(snapshot.bms_events),
                choch_events=self._serialize_choch_events(snapshot.choch_events),
                sms_events=self._serialize_sms_events(snapshot.sms_events),
                order_blocks=self._serialize_order_blocks(snapshot.order_blocks),
                fair_value_gaps=self._serialize_fvgs(snapshot.fvgs),
                liquidity_sweeps=self._serialize_sweeps(snapshot.liquidity_sweeps),
                inducement_events=self._serialize_inducements(snapshot.inducement_events),
                qm_levels=self._serialize_qm_levels(snapshot.qml_levels),
                sr_flips=self._serialize_sr_flips(snapshot.sr_flips),
                rs_flips=self._serialize_rs_flips(snapshot.rs_flips),
                previous_levels=self._serialize_previous_levels(snapshot),
                mpl_levels=self._serialize_mpl_levels(snapshot.mpl_levels),
                fakeout_tests=self._serialize_fakeout_tests(snapshot),
                supply_zones=self._serialize_supply_zones(snapshot.supply_zones),
                demand_zones=self._serialize_demand_zones(snapshot.demand_zones),
                fibonacci_retracements=self._serialize_fibonacci(snapshot.fibonacci_retracements),
            )
        except Exception as e:
            self._logger.error(
                "snapshot_persistence_failed",
                extra={
                    "symbol": snapshot.symbol,
                    "timeframe": snapshot.timeframe.value,
                    "error": str(e),
                },
                exc_info=True,
            )

    # ── Full snapshot serializer ─────────────────────────────────────

    def _serialize_snapshot(self, snapshot: TechnicalSnapshot) -> dict:
        """Serialize a full TechnicalSnapshot into a dict for the result payload."""
        return {
            "symbol": snapshot.symbol,
            "timeframe": snapshot.timeframe.value,
            "timestamp": snapshot.timestamp.isoformat(),
            "candle_count": snapshot.candle_count,
            "trend_direction": snapshot.trend_direction.value,
            "swing_highs": self._serialize_swing_highs(snapshot.swing_highs),
            "swing_lows": self._serialize_swing_lows(snapshot.swing_lows),
            "bms_events": self._serialize_bms_events(snapshot.bms_events),
            "choch_events": self._serialize_choch_events(snapshot.choch_events),
            "sms_events": self._serialize_sms_events(snapshot.sms_events),
            "order_blocks": self._serialize_order_blocks(snapshot.order_blocks),
            "fair_value_gaps": self._serialize_fvgs(snapshot.fvgs),
            "liquidity_sweeps": self._serialize_sweeps(snapshot.liquidity_sweeps),
            "inducement_events": self._serialize_inducements(snapshot.inducement_events),
            "qm_levels": self._serialize_qm_levels(snapshot.qml_levels),
            "sr_flips": self._serialize_sr_flips(snapshot.sr_flips),
            "rs_flips": self._serialize_rs_flips(snapshot.rs_flips),
            "mpl_levels": self._serialize_mpl_levels(snapshot.mpl_levels),
            "supply_zones": self._serialize_supply_zones(snapshot.supply_zones),
            "demand_zones": self._serialize_demand_zones(snapshot.demand_zones),
            "fibonacci_retracements": self._serialize_fibonacci(snapshot.fibonacci_retracements),
            "total_structure_events": snapshot.total_structure_events,
            "total_liquidity_events": snapshot.total_liquidity_events,
            "total_zones": snapshot.total_zones,
        }

    # ── Per-field serializers ────────────────────────────────────────

    @staticmethod
    def _serialize_swing_highs(swing_highs: list) -> dict:
        return {
            "count": len(swing_highs),
            "data": [
                {
                    "price": sh.price,
                    "timestamp": sh.timestamp.isoformat(),
                    "index": sh.index,
                    "strength": sh.strength,
                    "timeframe": sh.timeframe.value,
                }
                for sh in swing_highs
            ],
        }

    @staticmethod
    def _serialize_swing_lows(swing_lows: list) -> dict:
        return {
            "count": len(swing_lows),
            "data": [
                {
                    "price": sl.price,
                    "timestamp": sl.timestamp.isoformat(),
                    "index": sl.index,
                    "strength": sl.strength,
                    "timeframe": sl.timeframe.value,
                }
                for sl in swing_lows
            ],
        }

    @staticmethod
    def _serialize_bms_events(bms_events: list) -> dict:
        return {
            "count": len(bms_events),
            "data": [
                {
                    "breakout_price": bms.breakout_price,
                    "broken_level": bms.broken_level,
                    "timestamp": bms.timestamp.isoformat(),
                    "direction": bms.direction.value,
                    "displacement_pips": bms.displacement_pips,
                    "timeframe": bms.timeframe.value,
                    "confirmed": bms.confirmed,
                }
                for bms in bms_events
            ],
        }

    @staticmethod
    def _serialize_choch_events(choch_events: list) -> dict:
        return {
            "count": len(choch_events),
            "data": [
                {
                    "breakout_price": choch.breakout_price,
                    "broken_level": choch.broken_level,
                    "timestamp": choch.timestamp.isoformat(),
                    "direction": choch.direction.value,
                    "timeframe": choch.timeframe.value,
                    "is_minor": choch.is_minor,
                }
                for choch in choch_events
            ],
        }

    @staticmethod
    def _serialize_sms_events(sms_events: list) -> dict:
        return {
            "count": len(sms_events),
            "data": [
                {
                    "failed_level": sms.failed_level,
                    "reversal_price": sms.reversal_price,
                    "timestamp": sms.timestamp.isoformat(),
                    "direction": sms.direction.value,
                    "timeframe": sms.timeframe.value,
                    "is_failure_swing": sms.is_failure_swing,
                }
                for sms in sms_events
            ],
        }

    @staticmethod
    def _serialize_order_blocks(order_blocks: list) -> dict:
        return {
            "count": len(order_blocks),
            "data": [
                {
                    "upper_bound": ob.upper_bound,
                    "lower_bound": ob.lower_bound,
                    "timestamp": ob.timestamp.isoformat(),
                    "direction": ob.direction.value,
                    "displacement_pips": ob.displacement_pips,
                    "is_breaker": ob.is_breaker,
                    "mitigated": ob.mitigated,
                    "timeframe": ob.timeframe.value,
                    "candle_index": ob.candle_index,
                }
                for ob in order_blocks
            ],
        }

    @staticmethod
    def _serialize_fvgs(fvgs: list) -> dict:
        return {
            "count": len(fvgs),
            "data": [
                {
                    "upper_bound": fvg.upper_bound,
                    "lower_bound": fvg.lower_bound,
                    "timestamp": fvg.timestamp.isoformat(),
                    "direction": fvg.direction.value,
                    "filled": fvg.filled,
                    "fill_percentage": fvg.fill_percentage,
                    "timeframe": fvg.timeframe.value,
                    "candle_index": fvg.candle_index,
                }
                for fvg in fvgs
            ],
        }

    @staticmethod
    def _serialize_sweeps(sweeps: list) -> dict:
        return {
            "count": len(sweeps),
            "data": [
                {
                    "swept_level": sweep.swept_level,
                    "timestamp": sweep.timestamp.isoformat(),
                    "liquidity_type": sweep.liquidity_type.value,
                    "sweep_pips": sweep.sweep_pips,
                    "closed_back_inside": sweep.closed_back_inside,
                }
                for sweep in sweeps
            ],
        }

    @staticmethod
    def _serialize_inducements(inducements: list) -> dict:
        return {
            "count": len(inducements),
            "data": [
                {
                    "price": ind.price,
                    "timestamp": ind.timestamp.isoformat(),
                    "direction": ind.direction.value,
                    "cleared": ind.cleared,
                }
                for ind in inducements
            ],
        }

    @staticmethod
    def _serialize_qm_levels(qm_levels: list) -> dict:
        return {
            "count": len(qm_levels),
            "data": [
                {
                    "qml_price": qm.qml_price,
                    "timestamp": qm.timestamp.isoformat(),
                    "direction": qm.direction.value,
                    "h_price": qm.h_price,
                    "hh_price": qm.hh_price,
                    "h_timestamp": qm.h_timestamp.isoformat(),
                    "hh_timestamp": qm.hh_timestamp.isoformat(),
                    "tested": qm.tested,
                    "timeframe": qm.timeframe.value,
                }
                for qm in qm_levels
            ],
        }

    @staticmethod
    def _serialize_sr_flips(sr_flips: list) -> dict:
        return {
            "count": len(sr_flips),
            "data": [
                {
                    "flip_level": sr.flip_level,
                    "breakout_price": sr.breakout_price,
                    "timestamp": sr.timestamp.isoformat(),
                    "previous_role": sr.previous_role,
                    "new_role": sr.new_role,
                    "timeframe": sr.timeframe.value,
                }
                for sr in sr_flips
            ],
        }

    @staticmethod
    def _serialize_rs_flips(rs_flips: list) -> dict:
        return {
            "count": len(rs_flips),
            "data": [
                {
                    "flip_level": rs.flip_level,
                    "breakout_price": rs.breakout_price,
                    "timestamp": rs.timestamp.isoformat(),
                    "previous_role": rs.previous_role,
                    "new_role": rs.new_role,
                    "timeframe": rs.timeframe.value,
                }
                for rs in rs_flips
            ],
        }

    @staticmethod
    def _serialize_supply_zones(supply_zones: list) -> dict:
        return {
            "count": len(supply_zones),
            "data": [
                {
                    "upper_bound": sz.upper_bound,
                    "lower_bound": sz.lower_bound,
                    "timestamp": sz.timestamp.isoformat(),
                    "strength": sz.strength,
                    "tested": sz.tested,
                    "test_count": sz.test_count,
                    "broken": sz.broken,
                    "timeframe": sz.timeframe.value,
                }
                for sz in supply_zones
            ],
        }

    @staticmethod
    def _serialize_demand_zones(demand_zones: list) -> dict:
        return {
            "count": len(demand_zones),
            "data": [
                {
                    "upper_bound": dz.upper_bound,
                    "lower_bound": dz.lower_bound,
                    "timestamp": dz.timestamp.isoformat(),
                    "strength": dz.strength,
                    "tested": dz.tested,
                    "test_count": dz.test_count,
                    "broken": dz.broken,
                    "timeframe": dz.timeframe.value,
                }
                for dz in demand_zones
            ],
        }

    @staticmethod
    def _serialize_fibonacci(fibonacci_retracements: list) -> dict:
        return {
            "count": len(fibonacci_retracements),
            "data": [
                {
                    "swing_high": fib.swing_high,
                    "swing_low": fib.swing_low,
                    "swing_high_timestamp": fib.swing_high_timestamp.isoformat(),
                    "swing_low_timestamp": fib.swing_low_timestamp.isoformat(),
                    "is_bullish": fib.is_bullish,
                }
                for fib in fibonacci_retracements
            ],
        }

    @staticmethod
    def _serialize_mpl_levels(mpl_levels: list) -> dict:
        return {
            "count": len(mpl_levels),
            "data": [
                {
                    "mpl_price": mpl.mpl_price,
                    "timestamp": mpl.timestamp.isoformat(),
                    "direction": mpl.direction.value,
                    "has_internal_structure": mpl.has_internal_structure,
                    "tested": mpl.tested,
                    "timeframe": mpl.timeframe.value,
                }
                for mpl in mpl_levels
            ],
        }

    @staticmethod
    def _serialize_previous_levels(snapshot: TechnicalSnapshot) -> dict:
        """Serialize equal highs/lows from the snapshot."""
        return {
            "count": len(snapshot.equal_highs_lows),
            "data": [
                {
                    "price": ehl.price,
                    "timestamp": ehl.timestamp.isoformat(),
                    "direction": ehl.direction.value,
                }
                for ehl in snapshot.equal_highs_lows
                if hasattr(ehl, "price")
            ],
        }

    @staticmethod
    def _serialize_fakeout_tests(snapshot: TechnicalSnapshot) -> dict:
        """Serialize liquidity grabs as fakeout tests from the snapshot."""
        return {
            "count": len(snapshot.liquidity_grabs),
            "data": [
                {
                    "price": grab.price,
                    "timestamp": grab.timestamp.isoformat(),
                    "direction": grab.direction.value,
                }
                for grab in snapshot.liquidity_grabs
                if hasattr(grab, "price")
            ],
        }
