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
from engine.ta.common.analyzers.candles import CandleAnalyzer
from engine.ta.common.analyzers.compression import CompressionAnalyzer
from engine.ta.common.analyzers.dealing_range import DealingRangeAnalyzer
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.analyzers.liquidity import LiquidityAnalyzer
from engine.ta.common.analyzers.marubozu import MarubozuAnalyzer
from engine.ta.common.analyzers.session import SessionAnalyzer
from engine.ta.common.analyzers.sweeps import SweepAnalyzer
from engine.ta.common.analyzers.swings import SwingAnalyzer
from engine.ta.common.services.alignment.service import AlignmentService
from engine.ta.common.services.snapshot.builder import SnapshotBuilder
from engine.ta.common.timeframe.manager import TimeframeManager
from engine.ta.constants import TIMEFRAME_MINUTES, Direction, Session, Timeframe
from engine.ta.models.candle import Candle, CandleSequence
from engine.ta.models.candidate import SMCCandidate, SnDCandidate
from engine.ta.models.snapshot import MultiTimeframeSnapshot, TechnicalSnapshot
from engine.ta.smc.config import SMCConfig
from engine.ta.smc.detector import SMCDetector
from engine.ta.smc.detectors.bms import BMSDetector
from engine.ta.smc.detectors.choch import CHOCHDetector
from engine.ta.smc.detectors.inducement import InducementDetector
from engine.ta.smc.detectors.sms import SMSDetector
from engine.ta.smc.zones.breaker import BreakerDetector
from engine.ta.smc.zones.fvg import FVGDetector
from engine.ta.smc.zones.order_block import OrderBlockDetector
from engine.ta.snd.config import SnDConfig
from engine.ta.snd.detector import SnDDetector
from engine.ta.snd.detectors.mpl import MPLDetector
from engine.ta.snd.detectors.previous_levels import PreviousLevelDetector
from engine.ta.snd.detectors.qm import QMDetector
from engine.ta.snd.detectors.rs_flip import RSFlipDetector
from engine.ta.snd.detectors.sr_flip import SRFlipDetector
from engine.ta.snd.detectors.supply_demand import SupplyDemandDetector
from engine.ta.storage.uow import TAUOWFactory, TAReadUOWFactory

logger = get_logger(__name__)


class TAOrchestrator:
    """
    Multi-timeframe TA workflow orchestration.

    Coordinates a complete top-down analysis cycle for a single symbol:

    1. Fetch candles for every configured timeframe (HTF + LTF).
    2. Run per-timeframe structural detection (BMS, CHOCH, SMS, OBs,
       FVGs, sweeps, inducements, QML/QMH, SR/RS flips, MPL, supply/
       demand zones, fibonacci, dealing ranges, equal highs/lows).
    3. Build a fully populated TechnicalSnapshot per timeframe.
    4. Run SMC detection on every adjacent HTF pair.
    5. Run SnD detection on every adjacent HTF pair.
    6. Run SMC/SnD confirmation on every adjacent LTF pair.
    7. Align all snapshots via AlignmentService.
    8. Persist every per-timeframe snapshot and all candidates.
    9. Return a structured multi-timeframe result dict.

    The orchestrator reads timeframe lists from TAConfig — it never
    hardcodes which timeframes to analyze.
    """

    def __init__(
        self,
        broker_client: Optional[BrokerBase],
        ta_uow_factory: TAUOWFactory,
        ta_read_uow_factory: TAReadUOWFactory,
        smc_detector: SMCDetector,
        snd_detector: SnDDetector,
        snapshot_builder: SnapshotBuilder,
        alignment_service: AlignmentService,
        timeframe_manager: TimeframeManager,
        ta_config: Optional[TAConfig] = None,
        fallback_client: Optional[BrokerBase] = None,
    ) -> None:
        self.broker_client = broker_client
        self.fallback_client = fallback_client
        self._ta_uow_factory = ta_uow_factory
        self._ta_read_uow_factory = ta_read_uow_factory
        self.smc_detector = smc_detector
        self.snd_detector = snd_detector
        self.snapshot_builder = snapshot_builder
        self.alignment_service = alignment_service
        self.timeframe_manager = timeframe_manager
        self._config = ta_config or get_ta_config()
        self._logger = get_logger(__name__)

        # Per-timeframe structural detectors — reuse the same instances
        # that the SMC/SnD framework detectors use internally so that
        # detection logic is identical and there is zero duplication.
        self._swing_analyzer = snapshot_builder.swing_analyzer
        self._session_analyzer = snapshot_builder.session_analyzer
        self._liquidity_analyzer = snapshot_builder.liquidity_analyzer
        self._sweep_analyzer = snapshot_builder.sweep_analyzer
        self._fibonacci_analyzer = snapshot_builder.fibonacci_analyzer
        self._dealing_range_analyzer = snapshot_builder.dealing_range_analyzer

        # SMC primitive detectors — pull from the SMC detector so config
        # thresholds (displacement pips, sweep pips, etc.) are consistent.
        self._bms_detector = smc_detector.bms_detector
        self._choch_detector = smc_detector.choch_detector
        self._sms_detector = smc_detector.sms_detector
        self._inducement_detector = smc_detector.inducement_detector
        self._fvg_detector = smc_detector.fvg_detector
        self._ob_detector = smc_detector.ob_detector
        self._breaker_detector = smc_detector.breaker_detector
        self._zone_validator = smc_detector.zone_validator

        # SnD primitive detectors — pull from the SnD detector.
        self._qm_detector = snd_detector.qm_detector
        self._sr_flip_detector = snd_detector.sr_flip_detector
        self._rs_flip_detector = snd_detector.rs_flip_detector
        self._previous_level_detector = snd_detector.previous_level_detector
        self._mpl_detector = snd_detector.mpl_detector
        self._supply_demand_detector = snd_detector.supply_demand_detector

    # ── Public API ───────────────────────────────────────────────────

    async def analyze(
        self,
        symbol: str,
        lookback_periods: int = 500,
        *,
        broker_client: BrokerBase,
        user_id: str,
        pulse=None,
    ) -> dict:
        """
        Run a complete multi-timeframe top-down analysis for *symbol*.

        Args:
            symbol: The trading symbol to analyze (e.g. "EURUSD").
            lookback_periods: Number of candles to fetch per timeframe.
            broker_client: The user's broker client for candle fetching.
                Required. In multi-tenant mode, each user has their own
                MT5 broker connection. There is no fallback.
            user_id: The authenticated user's ID. Required. All storage
                operations (candle reads, snapshot writes, candidate
                writes) are scoped to this user.
            pulse: Optional PulsePublisher for real-time status updates.
                Fire-and-forget; ``None`` silently disables all pulses.

        Returns:
            Structured multi-timeframe analysis result dict.
        """
        active_broker = broker_client
        if active_broker is None:
            self._logger.error(
                "ta_analysis_no_broker",
                extra={"symbol": symbol},
            )
            return self._build_result(
                symbol=symbol,
                status="error",
                htf_timeframes=self._config.htf_timeframes,
                ltf_timeframes=self._config.ltf_timeframes,
                error="No broker connection configured. Please set up a broker connection via the dashboard.",
            )
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
                if pulse:
                    await pulse.emit("SHARDING", f"Fetching {tf.value} candle data")
                adaptive_lookback = self._get_adaptive_lookback(tf, lookback_periods)
                seq = await self._fetch_sequence(symbol, tf, adaptive_lookback, active_broker, user_id=user_id)
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

            # ── Phase 2: Per-timeframe structural detection + snapshot
            if pulse:
                await pulse.emit("SHARDING", "Candle acquisition complete", completed=True)
            snapshots: dict[Timeframe, TechnicalSnapshot] = {}
            for tf, seq in sequences.items():
                if pulse:
                    await pulse.emit("DETECTING", f"Analyzing {tf.value} market structure")
                snapshot = self._build_enriched_snapshot(seq)
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
            if pulse:
                await pulse.emit("DETECTING", "Structural analysis complete", completed=True)
            all_smc: list[SMCCandidate] = []
            all_snd: list[SnDCandidate] = []

            available_htfs = [tf for tf in htf_timeframes if tf in sequences]
            for i in range(len(available_htfs) - 1):
                higher_tf = available_htfs[i]
                lower_tf = available_htfs[i + 1]
                if pulse:
                    await pulse.emit("SHIMMING", f"Scanning {higher_tf.value}→{lower_tf.value} SMC zones")
                smc = self._run_smc_detection(
                    sequences[higher_tf],
                    sequences[lower_tf],
                )
                if pulse:
                    await pulse.emit("SHIMMING", f"Scanning {higher_tf.value}→{lower_tf.value} SnD zones")
                snd = self._run_snd_detection(
                    sequences[higher_tf],
                    sequences[lower_tf],
                )
                all_smc.extend(smc)
                all_snd.extend(snd)

            # ── Phase 4: Run confirmation detection on LTF pairs ─────
            available_ltfs = [tf for tf in ltf_timeframes if tf in sequences]
            for i in range(len(available_ltfs) - 1):
                higher_tf = available_ltfs[i]
                lower_tf = available_ltfs[i + 1]
                if pulse:
                    await pulse.emit("PONTIFICATING", f"LTF confirmation {higher_tf.value}→{lower_tf.value}")
                smc = self._run_smc_detection(
                    sequences[higher_tf],
                    sequences[lower_tf],
                )
                snd = self._run_snd_detection(
                    sequences[higher_tf],
                    sequences[lower_tf],
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
                    and self.timeframe_manager.is_htf_of(
                        lowest_htf,
                        highest_ltf,
                    )
                ):
                    smc = self._run_smc_detection(
                        sequences[lowest_htf],
                        sequences[highest_ltf],
                    )
                    snd = self._run_snd_detection(
                        sequences[lowest_htf],
                        sequences[highest_ltf],
                    )
                    all_smc.extend(smc)
                    all_snd.extend(snd)

            # ── Phase 6: Align adjacent snapshots ────────────────────
            if pulse:
                await pulse.emit("SHIMMING", "Zone scanning complete", completed=True)
                await pulse.emit("FERMENTING", "Performing multi-timeframe trend alignment")
            alignments: dict[str, dict] = {}
            ordered_tfs = [tf for tf in all_timeframes if tf in snapshots]
            for i in range(len(ordered_tfs) - 1):
                higher_tf = ordered_tfs[i]
                lower_tf = ordered_tfs[i + 1]
                alignment_key = f"{higher_tf.value}_{lower_tf.value}"
                mtf_snap = self.alignment_service.check_alignment(
                    snapshots[higher_tf],
                    snapshots[lower_tf],
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
                snapshots,
                ordered_tfs,
            )

            # ── Phase 8: Deduplicate candidates across timeframe pairs ─
            if pulse:
                await pulse.emit("FERMENTING", "Deduplicating candidates")
            all_smc = self._deduplicate_smc_candidates(all_smc)
            all_snd = self._deduplicate_snd_candidates(all_snd)

            # ── Phase 9: Persist all results ─────────────────────────
            if pulse:
                await pulse.emit("ACTIONING", "Persisting analysis results")
            await self._persist_all_results(
                snapshots,
                all_smc,
                all_snd,
                user_id=user_id,
            )

            if pulse:
                await pulse.emit(
                    "FERMENTING",
                    f"TA complete — {len(all_smc)} SMC, {len(all_snd)} SnD candidates",
                    completed=True,
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
        """Build the structured result dict returned by analyze().

        Single chokepoint where the in-memory algorithmic truth is
        converted into the dict that crosses the HTTP boundary to the
        gateway and ultimately reaches the LLM prompt builder.

        Filtering happens here -- AFTER detection has finished AND
        AFTER persistence has captured the full state to the database
        (Phase 9 of analyze()). The algorithm and the DB therefore see
        EVERY structure the detectors produced; only the prompt path
        sees the trimmed view.

        Filters applied:
          1. Snapshot serialisation drops dead structures (mitigated
             OBs, mitigated breakers, filled FVGs, tested QM levels,
             tested MPLs) inside ``_serialize_snapshot``. The per-field
             serializers themselves remain faithful object->dict
             transformers because they are ALSO used by
             ``_persist_snapshot`` which must preserve full fidelity.
          2. Candidate dumps drop entries whose underlying POI (OB,
             FVG, QM) is already dead. Cross-referenced by timestamp
             against the parent snapshot's mitigated/filled/tested
             events.
          3. The alignment block is flattened: each pair previously
             carried both flat fields and an identical nested
             ``alignment_metadata`` block. ``zones_nested`` is promoted
             to a top-level field and the nested block is dropped.
        """
        smc_list = smc_candidates or []
        snd_list = snd_candidates or []
        snapshot_map = snapshots or {}

        serialized_snapshots: dict[str, dict] = {}
        for tf, snap in snapshot_map.items():
            serialized_snapshots[tf.value] = self._serialize_snapshot(snap)

        # -- Candidate POI-validity filter ----------------------------
        # A candidate whose anchor POI is mitigated, filled, or tested
        # cannot be a live tradeable setup. POI-validity is the criterion,
        # not age: a months-old candidate whose OB is still unmitigated
        # remains because price can return to that OB today.
        dead_ob_timestamps: set = set()
        dead_fvg_timestamps: set = set()
        dead_qm_timestamps: set = set()
        for snap in snapshot_map.values():
            for ob in snap.order_blocks:
                if ob.mitigated:
                    dead_ob_timestamps.add(ob.timestamp)
            for fvg in snap.fvgs:
                if fvg.filled:
                    dead_fvg_timestamps.add(fvg.timestamp)
            for qm in snap.qml_levels:
                if qm.tested:
                    dead_qm_timestamps.add(qm.timestamp)

        def _smc_is_live(c: SMCCandidate) -> bool:
            """SMC candidate dies when its anchor OB is mitigated OR
            its anchor FVG is filled. Candidates without either anchor
            (e.g. pure turtle-soup variants) pass through unchanged.
            """
            if (
                c.order_block_timestamp is not None
                and c.order_block_timestamp in dead_ob_timestamps
            ):
                return False
            if (
                c.fvg_timestamp is not None
                and c.fvg_timestamp in dead_fvg_timestamps
            ):
                return False
            return True

        def _snd_is_live(c: SnDCandidate) -> bool:
            """SnD candidate dies when its anchor QM level has been
            tested. SR/RS flips and fakeouts have no consumed flag.
            """
            if (
                c.qml_timestamp is not None
                and c.qml_timestamp in dead_qm_timestamps
            ):
                return False
            return True

        live_smc = [c for c in smc_list if _smc_is_live(c)]
        live_snd = [c for c in snd_list if _snd_is_live(c)]

        if len(live_smc) != len(smc_list) or len(live_snd) != len(snd_list):
            self._logger.info(
                "candidates_dead_poi_filtered",
                extra={
                    "symbol": symbol,
                    "smc_before": len(smc_list),
                    "smc_after": len(live_smc),
                    "smc_dropped": len(smc_list) - len(live_smc),
                    "snd_before": len(snd_list),
                    "snd_after": len(live_snd),
                    "snd_dropped": len(snd_list) - len(live_snd),
                    "dead_obs": len(dead_ob_timestamps),
                    "dead_fvgs": len(dead_fvg_timestamps),
                    "dead_qms": len(dead_qm_timestamps),
                },
            )

        # -- Alignment block flattening -------------------------------
        # Each pair previously carried both flat fields AND an identical
        # nested ``alignment_metadata`` block. Promote ``zones_nested``
        # to top-level and drop the nested block.
        flat_alignments: dict[str, dict] = {}
        for pair_key, pair_data in (alignments or {}).items():
            metadata = pair_data.get("alignment_metadata") or {}
            zones_nested = metadata.get("zones_nested")
            flat_entry = {
                k: v for k, v in pair_data.items()
                if k != "alignment_metadata"
            }
            if zones_nested is not None:
                flat_entry["zones_nested"] = zones_nested
            flat_alignments[pair_key] = flat_entry

        serialized_smc = [
            c.model_dump(mode="json") if hasattr(c, "model_dump") else {}
            for c in live_smc
        ]
        serialized_snd = [
            c.model_dump(mode="json") if hasattr(c, "model_dump") else {}
            for c in live_snd
        ]

        return {
            "status": status,
            "symbol": symbol,
            "htf_timeframes": [tf.value for tf in htf_timeframes],
            "ltf_timeframes": [tf.value for tf in ltf_timeframes],
            "snapshots": serialized_snapshots,
            "smc_candidates": serialized_smc,
            "snd_candidates": serialized_snd,
            "smc_candidates_count": len(live_smc),
            "snd_candidates_count": len(live_snd),
            "alignment": flat_alignments,
            "overall_trend": overall_trend,
            "error": error,
        }

    # ── Candle fetching ──────────────────────────────────────────────

    async def _fetch_sequence(
        self,
        symbol: str,
        timeframe: Timeframe,
        lookback_periods: int,
        broker: BrokerBase,
        *,
        user_id: str,
    ) -> Optional[CandleSequence]:
        """Fetch candles for a single timeframe from store or broker.

        Args:
            broker: The user's broker client. Required. No fallback.
            user_id: The authenticated user's ID. Candle reads are
                scoped to this user.
        """
        end_time = datetime.now(UTC)
        start_time = self._calculate_start_time(
            end_time,
            timeframe,
            lookback_periods,
        )

        async with self._ta_read_uow_factory() as uow:
            stored_rows = await uow.candle_repo.find_by_time_range(
                symbol,
                timeframe.value,
                start_time,
                end_time,
                user_id=user_id,
            )

        active_broker = broker

        if len(stored_rows) < lookback_periods * 0.8:
            if active_broker is None:
                self._logger.warning(
                    "no_broker_available_for_candle_fetch",
                    extra={
                        "symbol": symbol,
                        "timeframe": timeframe.value,
                        "stored_count": len(stored_rows),
                    },
                )
            else:
                self._logger.info(
                    "fetching_candles_from_broker",
                    extra={
                        "symbol": symbol,
                        "timeframe": timeframe.value,
                        "stored_count": len(stored_rows),
                        "required_count": lookback_periods,
                    },
                )
                try:
                    sequence = await active_broker.fetch_candles(
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

                if self.fallback_client:
                    self._logger.info(
                        "attempting_fallback_broker",
                        extra={
                            "symbol": symbol,
                            "timeframe": timeframe.value,
                        },
                    )
                    try:
                        fb_sequence = await self.fallback_client.fetch_candles(
                            symbol=symbol,
                            timeframe=timeframe,
                            start_time=start_time,
                            end_time=end_time,
                            count=lookback_periods,
                        )
                        if fb_sequence and fb_sequence.count > 0:
                            return fb_sequence
                    except Exception as fb_e:
                        self._logger.error(
                            "fallback_broker_fetch_failed",
                            extra={
                                "symbol": symbol,
                                "timeframe": timeframe.value,
                                "error": str(fb_e),
                            },
                            exc_info=True,
                        )

        if not stored_rows:
            self._logger.warning(
                "no_candle_data_available",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe.value,
                },
            )
            return None

        # Convert CandleSchema ORM rows to Candle domain models.
        candles = [
            Candle(
                symbol=row.symbol,
                timeframe=Timeframe(row.timeframe),
                timestamp=row.timestamp,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume if row.volume is not None else 0.0,
            )
            for row in stored_rows
        ]

        return CandleSequence(
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
        )

    @staticmethod
    def _calculate_start_time(
        end_time: datetime,
        timeframe: Timeframe,
        lookback_periods: int,
    ) -> datetime:
        """Calculate start time using TIMEFRAME_MINUTES."""
        minutes = TIMEFRAME_MINUTES.get(timeframe)
        if minutes is None:
            raise ValueError(f"Unknown timeframe: {timeframe}")
        return end_time - timedelta(minutes=minutes * lookback_periods)

    @staticmethod
    def _get_adaptive_lookback(timeframe: Timeframe, default_lookback: int) -> int:
        """
        Derive dynamic lookback periods depending on the timeframe.
        HTFs require far fewer candles (preventing decades of irrelevant data),
        while LTFs need more to maintain structural integrity.
        """
        mapping = {
            Timeframe.MN1: 72,
            Timeframe.W1: 250,
            Timeframe.D1: 60,
            Timeframe.H12: 80,
            Timeframe.H8: 100,
            Timeframe.H6: 120,
            Timeframe.H4: 150,
            Timeframe.H3: 200,
            Timeframe.H1: 300,
            Timeframe.M30: 500,
            Timeframe.M15: 750,
            Timeframe.M5: 1000,
            Timeframe.M1: 1500,
        }
        return mapping.get(timeframe, default_lookback)

    # ── Per-timeframe structural detection + enriched snapshot ────────

    def _build_enriched_snapshot(
        self,
        sequence: CandleSequence,
    ) -> Optional[TechnicalSnapshot]:
        """
        Run ALL per-timeframe structural detection and build a fully
        populated TechnicalSnapshot.
        It runs
        every detector on the single-timeframe candle data and feeds all
        results into the SnapshotBuilder so the snapshot contains the
        complete structural context (BMS, CHOCH, SMS, OBs, FVGs, sweeps,
        inducements, QML/QMH, SR/RS flips, MPL, supply/demand zones,
        fibonacci retracements, dealing ranges, equal highs/lows).
        """
        try:
            # ── Swing detection ──────────────────────────────────────
            swing_highs = self._swing_analyzer.detect_swing_highs(sequence)
            swing_lows = self._swing_analyzer.detect_swing_lows(sequence)

            # ── SMC structure events ─────────────────────────────────
            # Bullish BMS = price breaks above a previous swing HIGH.
            # Bearish BMS = price breaks below a previous swing LOW.
            bms_bullish = self._bms_detector.detect_bullish_bms(
                sequence,
                swing_highs,
            )
            bms_bearish = self._bms_detector.detect_bearish_bms(
                sequence,
                swing_lows,
            )
            all_bms = bms_bullish + bms_bearish

            # Bullish ChoCH = price breaks above a minor swing HIGH.
            # Bearish ChoCH = price breaks below a minor swing LOW.
            choch_bullish = self._choch_detector.detect_bullish_choch(
                sequence,
                swing_highs,
            )
            choch_bearish = self._choch_detector.detect_bearish_choch(
                sequence,
                swing_lows,
            )
            all_choch = choch_bullish + choch_bearish

            sms_bullish = self._sms_detector.detect_bullish_sms(
                sequence,
                swing_lows,
            )
            sms_bearish = self._sms_detector.detect_bearish_sms(
                sequence,
                swing_highs,
            )
            all_sms = sms_bullish + sms_bearish

            # ── SMC zones ────────────────────────────────────────────
            fvgs = self._fvg_detector.detect_fvgs(sequence)

            order_blocks = []
            for bms_event in all_bms:
                if bms_event.direction == Direction.BULLISH:
                    ob = self._ob_detector.detect_bullish_ob(
                        sequence,
                        bms_event,
                    )
                else:
                    ob = self._ob_detector.detect_bearish_ob(
                        sequence,
                        bms_event,
                    )
                if ob is not None:
                    order_blocks.append(ob)

            # ── OB mitigation check (body-threshold) ──────────────────
            # Mark OBs as mitigated using body-threshold analysis.
            # A wick retest (RTO) is the entry opportunity, NOT
            # mitigation.  Only when a candle body closes decisively
            # through the zone (>= configured threshold, default 50%)
            # is the OB considered consumed.
            #
            # Uses ZoneValidator.validate_zone_freshness() - the single
            # source of truth for mitigation across the entire system.
            #
            # OrderBlock extends FrozenModel so we use model_copy()
            # to produce an updated instance.
            for idx, ob in enumerate(order_blocks):
                is_fresh = self._zone_validator.validate_zone_freshness(
                    ob, sequence,
                )
                if not is_fresh:
                    order_blocks[idx] = ob.model_copy(
                        update={
                            "mitigated": True,
                        },
                    )

            breaker_blocks = []
            for ob in order_blocks:
                breaker = self._breaker_detector.detect_breaker_from_ob(
                    sequence,
                    ob,
                )
                if breaker is not None:
                    breaker_blocks.append(breaker)

            # ── SMC liquidity / inducement ───────────────────────────
            inducement_bullish = self._inducement_detector.detect_bullish_inducement(
                sequence,
                swing_lows,
            )
            inducement_bearish = self._inducement_detector.detect_bearish_inducement(
                sequence,
                swing_highs,
            )
            all_inducements = inducement_bullish + inducement_bearish

            liquidity_sweeps = self._sweep_analyzer.detect_sweeps_in_sequence(
                sequence,
                swing_highs,
                swing_lows,
            )

            # ── Liquidity pools and equal highs/lows ─────────────────
            equal_highs = self._liquidity_analyzer.detect_equal_highs(
                swing_highs,
            )
            equal_lows = self._liquidity_analyzer.detect_equal_lows(
                swing_lows,
            )
            all_equal_highs_lows = equal_highs + equal_lows

            # ── SnD structure events ─────────────────────────────────
            sr_flips = self._sr_flip_detector.detect_sr_flips(
                sequence,
                swing_lows,
            )
            rs_flips = self._rs_flip_detector.detect_rs_flips(
                sequence,
                swing_highs,
            )

            qml_levels = self._qm_detector.detect_qml(
                sequence,
                swing_highs,
                swing_lows,
            )
            qmh_levels = self._qm_detector.detect_qmh(
                sequence,
                swing_lows,
                swing_highs,
            )
            all_qm_levels = qml_levels + qmh_levels

            # ── SnD supply/demand zones ──────────────────────────────
            supply_zones = []
            demand_zones = []
            for qml in qml_levels:
                for sr_flip in sr_flips:
                    sz = self._supply_demand_detector.create_supply_zone(
                        sequence,
                        qml.level,
                        qml.timestamp,
                        sr_flip.new_resistance_level,
                        sr_flip.timestamp,
                    )
                    supply_zones.append(sz)

            for qmh in qmh_levels:
                for rs_flip in rs_flips:
                    dz = self._supply_demand_detector.create_demand_zone(
                        sequence,
                        qmh.level,
                        qmh.timestamp,
                        rs_flip.new_support_level,
                        rs_flip.timestamp,
                    )
                    demand_zones.append(dz)

            # ── Fibonacci retracements ───────────────────────────────
            fibonacci_retracements = []
            if swing_highs and swing_lows:
                latest_high = self._swing_analyzer.get_latest_swing_high(
                    swing_highs,
                )
                latest_low = self._swing_analyzer.get_latest_swing_low(
                    swing_lows,
                )
                if latest_high and latest_low:
                    is_bullish = latest_low.timestamp > latest_high.timestamp
                    fib = self._fibonacci_analyzer.create_retracement(
                        latest_high,
                        latest_low,
                        is_bullish,
                    )
                    fibonacci_retracements.append(fib)

            # ── Dealing ranges (from session data) ───────────────────
            dealing_ranges = []
            for session in (Session.ASIA, Session.LONDON, Session.NEW_YORK):
                session_range = self._session_analyzer.extract_session_range(
                    sequence,
                    session,
                )
                if session_range is not None:
                    dr = self._dealing_range_analyzer.create_from_session(
                        session_range,
                    )
                    if dr is not None:
                        dealing_ranges.append(dr)

            # ── Build the fully populated snapshot ────────────────────
            snapshot = self.snapshot_builder.build_snapshot(
                candles=sequence,
                bms_events=all_bms,
                choch_events=all_choch,
                sms_events=all_sms,
                sr_flips=sr_flips,
                rs_flips=rs_flips,
                liquidity_sweeps=liquidity_sweeps,
                inducement_events=all_inducements,
                equal_highs_lows=all_equal_highs_lows,
                order_blocks=order_blocks,
                fvgs=fvgs,
                breaker_blocks=breaker_blocks,
                supply_zones=supply_zones,
                demand_zones=demand_zones,
                qml_levels=all_qm_levels,
                fibonacci_retracements=fibonacci_retracements,
                dealing_ranges=dealing_ranges,
            )

            self._logger.debug(
                "enriched_snapshot_built",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe.value,
                    "candle_count": sequence.count,
                    "swing_highs": len(swing_highs),
                    "swing_lows": len(swing_lows),
                    "bms_events": len(all_bms),
                    "choch_events": len(all_choch),
                    "sms_events": len(all_sms),
                    "order_blocks": len(order_blocks),
                    "fvgs": len(fvgs),
                    "breaker_blocks": len(breaker_blocks),
                    "liquidity_sweeps": len(liquidity_sweeps),
                    "inducements": len(all_inducements),
                    "equal_highs_lows": len(all_equal_highs_lows),
                    "sr_flips": len(sr_flips),
                    "rs_flips": len(rs_flips),
                    "qm_levels": len(all_qm_levels),
                    "supply_zones": len(supply_zones),
                    "demand_zones": len(demand_zones),
                    "fibonacci_retracements": len(fibonacci_retracements),
                    "dealing_ranges": len(dealing_ranges),
        
        
        
                    "trend_direction": snapshot.trend_direction.value,
                },
            )

            return snapshot

        except Exception as e:
            self._logger.error(
                "enriched_snapshot_build_failed",
                extra={
                    "symbol": sequence.symbol,
                    "timeframe": sequence.timeframe.value,
                    "error": str(e),
                },
                exc_info=True,
            )
            return None

    # ── Candidate deduplication ───────────────────────────────────────

    def _deduplicate_smc_candidates(
        self,
        candidates: list[SMCCandidate],
    ) -> list[SMCCandidate]:
        """Remove duplicate SMC candidates detected across timeframe pairs.

        Deduplicates by (symbol, pattern, direction, entry_price rounded to
        pip precision) so the same trade setup is only kept once, preferring
        the first (highest-timeframe) occurrence.
        """
        seen: set[tuple] = set()
        unique: list[SMCCandidate] = []
        for c in candidates:
            key = (c.symbol, c.pattern, c.direction, round(c.entry_price, 4))
            if key not in seen:
                seen.add(key)
                unique.append(c)
        if len(candidates) != len(unique):
            self._logger.info(
                "smc_candidates_deduplicated",
                extra={
                    "before": len(candidates),
                    "after": len(unique),
                    "removed": len(candidates) - len(unique),
                },
            )
        return unique

    def _deduplicate_snd_candidates(
        self,
        candidates: list[SnDCandidate],
    ) -> list[SnDCandidate]:
        """Remove duplicate SnD candidates detected across timeframe pairs."""
        seen: set[tuple] = set()
        unique: list[SnDCandidate] = []
        for c in candidates:
            key = (c.symbol, c.pattern, c.direction, round(c.entry_price, 4))
            if key not in seen:
                seen.add(key)
                unique.append(c)
        if len(candidates) != len(unique):
            self._logger.info(
                "snd_candidates_deduplicated",
                extra={
                    "before": len(candidates),
                    "after": len(unique),
                    "removed": len(candidates) - len(unique),
                },
            )
        return unique

    # ── Pattern detection ────────────────────────────────────────────

    def _run_smc_detection(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
    ) -> list[SMCCandidate]:
        """Run SMC pattern detection for one HTF/LTF pair.

        Exceptions are logged with full traceback and re-raised so the
        caller (analyze()) can capture them in its error result.  Silent
        swallowing of exceptions is not acceptable in a system that
        handles people's money.
        """
        self._logger.info(
            "smc_detection_pair_started",
            extra={
                "symbol": htf_sequence.symbol,
                "htf_timeframe": htf_sequence.timeframe.value,
                "ltf_timeframe": ltf_sequence.timeframe.value,
                "htf_candle_count": htf_sequence.count,
                "ltf_candle_count": ltf_sequence.count,
            },
        )
        try:
            candidates = self.smc_detector.detect_patterns(
                htf_sequence,
                ltf_sequence,
            )
            self._logger.info(
                "smc_detection_pair_completed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "htf_timeframe": htf_sequence.timeframe.value,
                    "ltf_timeframe": ltf_sequence.timeframe.value,
                    "candidates_count": len(candidates),
                    "candidate_patterns": [
                        c.pattern.value for c in candidates
                    ] if candidates else [],
                },
            )
            return candidates
        except Exception as e:
            self._logger.error(
                "smc_detection_pair_failed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "htf_timeframe": htf_sequence.timeframe.value,
                    "ltf_timeframe": ltf_sequence.timeframe.value,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    def _run_snd_detection(
        self,
        htf_sequence: CandleSequence,
        ltf_sequence: CandleSequence,
    ) -> list[SnDCandidate]:
        """Run SnD pattern detection for one HTF/LTF pair.

        Exceptions are logged with full traceback and re-raised.
        """
        self._logger.info(
            "snd_detection_pair_started",
            extra={
                "symbol": htf_sequence.symbol,
                "htf_timeframe": htf_sequence.timeframe.value,
                "ltf_timeframe": ltf_sequence.timeframe.value,
                "htf_candle_count": htf_sequence.count,
                "ltf_candle_count": ltf_sequence.count,
            },
        )
        try:
            candidates = self.snd_detector.detect_patterns(
                htf_sequence,
                ltf_sequence,
            )
            self._logger.info(
                "snd_detection_pair_completed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "htf_timeframe": htf_sequence.timeframe.value,
                    "ltf_timeframe": ltf_sequence.timeframe.value,
                    "candidates_count": len(candidates),
                    "candidate_patterns": [
                        c.pattern.value for c in candidates
                    ] if candidates else [],
                },
            )
            return candidates
        except Exception as e:
            self._logger.error(
                "snd_detection_pair_failed",
                extra={
                    "symbol": htf_sequence.symbol,
                    "htf_timeframe": htf_sequence.timeframe.value,
                    "ltf_timeframe": ltf_sequence.timeframe.value,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    # ── Overall trend ────────────────────────────────────────────────

    @staticmethod
    def _determine_overall_trend(
        snapshots: dict[Timeframe, TechnicalSnapshot],
        ordered_tfs: list[Timeframe],
    ) -> str:
        """
        Derive the overall market bias from the highest available
        timeframe. Falls through to the next highest if NEUTRAL.
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
        *,
        user_id: str,
    ) -> None:
        """Persist every per-timeframe snapshot and all candidates for user_id.

        Uses bulk candidate persistence to minimize DB round-trips:
        one dedup query + one flush per candidate type instead of
        one query + one flush per individual candidate.
        """
        smc_persisted = 0
        snd_persisted = 0

        async with self._ta_uow_factory() as uow:
            for tf, snapshot in snapshots.items():
                await self._persist_snapshot(snapshot, uow, user_id=user_id)

            try:
                smc_schemas = await uow.candidate_repo.bulk_create_smc_candidates(
                    smc_candidates,
                    user_id=user_id,
                )
                smc_persisted = len(smc_schemas)
            except Exception as e:
                self._logger.error(
                    "smc_candidates_bulk_persistence_failed",
                    extra={
                        "total_candidates": len(smc_candidates),
                        "error": str(e),
                    },
                    exc_info=True,
                )

            try:
                snd_schemas = await uow.candidate_repo.bulk_create_snd_candidates(
                    snd_candidates,
                    user_id=user_id,
                )
                snd_persisted = len(snd_schemas)
            except Exception as e:
                self._logger.error(
                    "snd_candidates_bulk_persistence_failed",
                    extra={
                        "total_candidates": len(snd_candidates),
                        "error": str(e),
                    },
                    exc_info=True,
                )

        self._logger.debug(
            "persistence_completed",
            extra={
                "snapshots_persisted": len(snapshots),
                "smc_candidates_total": len(smc_candidates),
                "smc_candidates_new": smc_persisted,
                "snd_candidates_total": len(snd_candidates),
                "snd_candidates_new": snd_persisted,
            },
        )

    async def _persist_snapshot(
        self,
        snapshot: TechnicalSnapshot,
        uow,
        *,
        user_id: str,
    ) -> None:
        """Persist a single TechnicalSnapshot to storage for user_id."""
        try:
            await uow.snapshot_repo.create(
                symbol=snapshot.symbol,
                timeframe=snapshot.timeframe.value,
                timestamp=snapshot.timestamp,
                user_id=user_id,
                swing_highs=self._serialize_swing_highs(
                    snapshot.swing_highs,
                ),
                swing_lows=self._serialize_swing_lows(
                    snapshot.swing_lows,
                ),
                bms_events=self._serialize_bms_events(
                    snapshot.bms_events,
                ),
                choch_events=self._serialize_choch_events(
                    snapshot.choch_events,
                ),
                sms_events=self._serialize_sms_events(
                    snapshot.sms_events,
                ),
                order_blocks=self._serialize_order_blocks(
                    snapshot.order_blocks,
                ),
                fair_value_gaps=self._serialize_fvgs(snapshot.fvgs),
                liquidity_sweeps=self._serialize_sweeps(
                    snapshot.liquidity_sweeps,
                ),
                inducement_events=self._serialize_inducements(
                    snapshot.inducement_events,
                ),
                qm_levels=self._serialize_qm_levels(
                    snapshot.qml_levels,
                ),
                sr_flips=self._serialize_sr_flips(snapshot.sr_flips),
                rs_flips=self._serialize_rs_flips(snapshot.rs_flips),
                previous_levels=self._serialize_previous_levels(
                    snapshot.equal_highs_lows,
                ),
                mpl_levels=self._serialize_mpl_levels(
                    snapshot.mpl_levels,
                ),
                fakeout_tests=self._serialize_liquidity_grabs(
                    snapshot.liquidity_grabs,
                ),
                supply_zones=self._serialize_supply_zones(
                    snapshot.supply_zones,
                ),
                demand_zones=self._serialize_demand_zones(
                    snapshot.demand_zones,
                ),
                fibonacci_retracements=self._serialize_fibonacci(
                    snapshot.fibonacci_retracements,
                ),
                breaker_blocks=self._serialize_breaker_blocks(
                    snapshot.breaker_blocks,
                ),
                dealing_ranges=self._serialize_dealing_ranges(
                    snapshot.dealing_ranges,
                ),
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
        """Serialize a TechnicalSnapshot into a dict for the prompt path.

        Dead structures are filtered BEFORE the trailing-N slice so the
        slice keeps the last N still-live items rather than N items
        that may include consumed POIs:

          - OrderBlock / BreakerBlock with mitigated=True are dropped.
          - FairValueGap with filled=True is dropped.
          - QuasiModoLevel / MiniPriceLevel with tested=True is dropped.

        Per-field serializers (``_serialize_order_blocks``,
        ``_serialize_fvgs``, ``_serialize_qm_levels`` etc.) are
        intentionally NOT modified -- they are dual-use, also called
        by ``_persist_snapshot`` which must capture full DB fidelity.
        Dead-structure filtering happens ONLY here, in the prompt-path
        serializer.

        Fields removed vs. the historical implementation:
          - ``candle_count`` (per-snapshot counter, not actionable)
          - ``total_structure_events`` / ``total_liquidity_events`` /
            ``total_zones`` (dashboard aggregates; the LLM reasons
            from the event arrays themselves)
        """
        live_obs = [ob for ob in snapshot.order_blocks if not ob.mitigated]
        live_breakers = [
            bb for bb in snapshot.breaker_blocks if not bb.mitigated
        ]
        live_fvgs = [fvg for fvg in snapshot.fvgs if not fvg.filled]
        live_qms = [qm for qm in snapshot.qml_levels if not qm.tested]
        live_mpls = [mpl for mpl in snapshot.mpl_levels if not mpl.tested]
        return {
            "symbol": snapshot.symbol,
            "timeframe": snapshot.timeframe.value,
            "timestamp": snapshot.timestamp.isoformat(),
#__BLANK_LINE_TO_REMOVE_NEXT_PASS__

            "trend_direction": snapshot.trend_direction.value,
            "swing_highs": self._serialize_swing_highs(snapshot.swing_highs[-12:]),
            "swing_lows": self._serialize_swing_lows(snapshot.swing_lows[-12:]),
            "bms_events": self._serialize_bms_events(snapshot.bms_events[-5:]),
            "choch_events": self._serialize_choch_events(snapshot.choch_events[-5:]),
            "sms_events": self._serialize_sms_events(snapshot.sms_events[-5:]),
            "order_blocks": self._serialize_order_blocks(live_obs[-5:]),
            "fair_value_gaps": self._serialize_fvgs(live_fvgs[-5:]),
            "breaker_blocks": self._serialize_breaker_blocks(live_breakers[-5:]),
            "liquidity_sweeps": self._serialize_sweeps(snapshot.liquidity_sweeps[-8:]),
            "inducement_events": self._serialize_inducements(
                snapshot.inducement_events[-5:]
            ),
            "equal_highs_lows": self._serialize_equal_highs_lows(
                snapshot.equal_highs_lows[-5:]
            ),
            "liquidity_grabs": self._serialize_liquidity_grabs(
                snapshot.liquidity_grabs[-5:]
            ),
            "qm_levels": self._serialize_qm_levels(live_qms[-5:]),
            "sr_flips": self._serialize_sr_flips(snapshot.sr_flips[-5:]),
            "rs_flips": self._serialize_rs_flips(snapshot.rs_flips[-5:]),
            "mpl_levels": self._serialize_mpl_levels(live_mpls[-5:]),
            "supply_zones": self._serialize_supply_zones(snapshot.supply_zones[-5:]),
            "demand_zones": self._serialize_demand_zones(snapshot.demand_zones[-5:]),
            "fibonacci_retracements": self._serialize_fibonacci(
                snapshot.fibonacci_retracements
            ),
            "dealing_ranges": self._serialize_dealing_ranges(snapshot.dealing_ranges[-3:]),
            
            
            
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
    def _serialize_breaker_blocks(breaker_blocks: list) -> dict:
        return {
            "count": len(breaker_blocks),
            "data": [
                {
                    "upper_bound": bb.upper_bound,
                    "lower_bound": bb.lower_bound,
                    "timestamp": bb.timestamp.isoformat(),
                    "direction": bb.direction.value,
                    "original_ob_timestamp": bb.original_ob_timestamp.isoformat(),
                    "broken_timestamp": bb.broken_timestamp.isoformat(),
                    "mitigated": bb.mitigated,
                    "timeframe": bb.timeframe.value,
                    "candle_index": bb.candle_index,
                }
                for bb in breaker_blocks
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
                    "timeframe": sweep.timeframe.value,
                    "candle_index": sweep.candle_index,
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
                    "inducement_level": ind.inducement_level,
                    "timestamp": ind.timestamp.isoformat(),
                    "direction": ind.direction.value,
                    "cleared": ind.cleared,
                    "cleared_timestamp": (
                        ind.cleared_timestamp.isoformat()
                        if ind.cleared_timestamp
                        else None
                    ),
                    "timeframe": ind.timeframe.value,
                    "is_internal": ind.is_internal,
                    "candle_index": ind.candle_index,
                }
                for ind in inducements
            ],
        }

    @staticmethod
    def _serialize_equal_highs_lows(equal_highs_lows: list) -> dict:
        return {
            "count": len(equal_highs_lows),
            "data": [
                {
                    "price_level": ehl.price_level,
                    "liquidity_type": ehl.liquidity_type.value,
                    "touch_count": ehl.touch_count,
                    "timestamps": [ts.isoformat() for ts in ehl.timestamps],
                    "tolerance_pips": ehl.tolerance_pips,
                    "timeframe": ehl.timeframe.value,
                    "swept": ehl.swept,
                }
                for ehl in equal_highs_lows
            ],
        }

    @staticmethod
    def _serialize_liquidity_grabs(liquidity_grabs: list) -> dict:
        return {
            "count": len(liquidity_grabs),
            "data": [
                {
                    "grab_price": grab.grab_price,
                    "grabbed_level": grab.grabbed_level,
                    "timestamp": grab.timestamp.isoformat(),
                    "direction": grab.direction.value,
                    "reversal_price": grab.reversal_price,
                    "confirmed": grab.confirmed,
                    "timeframe": grab.timeframe.value,
                    "candle_index": grab.candle_index,
                }
                for grab in liquidity_grabs
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
                    "range_size": fib.range_size,
                }
                for fib in fibonacci_retracements
            ],
        }

    @staticmethod
    def _serialize_dealing_ranges(dealing_ranges: list) -> dict:
        return {
            "count": len(dealing_ranges),
            "data": [
                {
                    "high": dr.high,
                    "low": dr.low,
                    "equilibrium": dr.equilibrium,
                    "start_time": dr.start_time.isoformat(),
                    "end_time": (dr.end_time.isoformat() if dr.end_time else None),
                    "timeframe": dr.timeframe.value,
                    "range_size": dr.range_size,
                }
                for dr in dealing_ranges
            ],
        }

    @staticmethod
    def _serialize_previous_levels(equal_highs_lows: list) -> dict:
        """Serialize equal highs/lows for DB persistence."""
        return {
            "count": len(equal_highs_lows),
            "data": [
                {
                    "price_level": ehl.price_level,
                    "liquidity_type": ehl.liquidity_type.value,
                    "touch_count": ehl.touch_count,
                    "timestamps": [ts.isoformat() for ts in ehl.timestamps],
                    "tolerance_pips": ehl.tolerance_pips,
                    "timeframe": ehl.timeframe.value,
                    "swept": ehl.swept,
                }
                for ehl in equal_highs_lows
            ],
        }
