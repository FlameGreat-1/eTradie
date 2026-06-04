"""Lightweight LTF confirmation service with HTF invalidation.

Designed for the execution watcher's fast-path confirmation pulse.
Two layers run in sequence, both purely mechanical (no LLM):

  Layer 1 - HTF Invalidation Check (~50-100ms)
    Fetches 50 candles on the HTF timeframe where the approved
    candidate's OB lives. Checks if the specific approved setup
    has been invalidated since the original analysis:
      - OB body mitigation (candle body closed through the zone)
      - Opposing BMS (new structure break against the trade direction)
      - Stop loss blown (price closed beyond the SL level)
    If invalidated -> return immediately, do NOT check LTF.

  Layer 2 - LTF Confirmation Check (~50-100ms)
    Fetches 150 candles on the LTF timeframe. Runs the 7 SMC
    confirmation checks. If all pass -> confirmed=True.

Total latency: ~100-200ms (two sequential broker fetches + scans).
This replaces the full TA pipeline re-run (~5-10s).
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from typing import Optional

from pydantic import BaseModel, Field

from engine.shared.logging import get_logger
from engine.ta.broker.base import BrokerBase
from engine.ta.common.analyzers.candles import CandleAnalyzer
from engine.ta.common.analyzers.session import SessionAnalyzer
from engine.ta.common.analyzers.sweeps import SweepAnalyzer
from engine.ta.common.analyzers.swings import SwingAnalyzer
from engine.ta.common.timeframe import get_parent_timeframe
from engine.ta.constants import Direction, Session, Timeframe, TIMEFRAME_MINUTES
from engine.ta.models.candle import CandleSequence
from engine.ta.smc.config import SMCConfig
from engine.ta.smc.detectors.bms import BMSDetector
from engine.ta.smc.detectors.choch import CHOCHDetector
from engine.ta.smc.detectors.inducement import InducementDetector
from engine.ta.smc.zones.fvg import FVGDetector

logger = get_logger(__name__)


class LTFConfirmationRequest(BaseModel):
    """Request payload for the lightweight LTF confirmation check."""
    symbol: str
    direction: str  # "BULLISH" or "BEARISH"
    ltf_timeframe: str  # e.g. "M5", "M15"
    ob_upper: float = Field(gt=0)
    ob_lower: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    trace_id: Optional[str] = None

    # Invalidation layer fields (optional for backward compatibility).
    # When provided, the service runs HTF invalidation checks before
    # the LTF confirmation checks.
    stop_loss: Optional[float] = Field(default=None, gt=0)
    htf_timeframe: Optional[str] = None  # e.g. "H4", "H1" - derived from LTF if not set


class LTFConfirmationResponse(BaseModel):
    """Response from the lightweight LTF confirmation check."""
    confirmed: bool
    symbol: str
    direction: str
    ltf_timeframe: str
    checks: dict  # Individual check results
    duration_ms: float
    error: Optional[str] = None

    # Invalidation layer results.
    invalidated: bool = False
    invalidation_reason: Optional[str] = None
    invalidation_checks: Optional[dict] = None


class LTFConfirmationService:
    """Lightweight LTF-only confirmation for execution watchers.

    Two-layer confirmation pipeline:

    Layer 1 - HTF Invalidation (runs first, fast-fails):
      1. OB body mitigation: candle body closed through the exact OB zone
      2. Opposing BMS: new structure break against the approved direction
      3. Stop loss blown: price closed beyond the SL level

    Layer 2 - LTF Confirmation (runs only if Layer 1 passes):
      1. Liquidity sweep (SSL/BSL taken and closed back inside)
      2. CHOCH on LTF (change of character)
      3. BMS on LTF (break in market structure)
      4. RTO to OB (current price inside the Order Block zone)
      5. Session timing (London/NY active)
      6. Inducement cleared
      7. FVG present on LTF

    All 7 LTF checks must be True for confirmed=True.
    Any single invalidation check failing returns confirmed=False + invalidated=True.
    """

    # Number of LTF candles to fetch for confirmation checks.
    LTF_LOOKBACK = 150

    # Number of HTF candles to fetch for invalidation checks.
    # Small lookback: we only need recent structure, not deep history.
    HTF_LOOKBACK = 50

    def __init__(
        self,
        smc_config: SMCConfig,
        swing_analyzer: SwingAnalyzer,
        session_analyzer: SessionAnalyzer,
        sweep_analyzer: SweepAnalyzer,
        candle_analyzer: CandleAnalyzer,
    ) -> None:
        self._config = smc_config
        self._swing_analyzer = swing_analyzer
        self._session_analyzer = session_analyzer
        self._sweep_analyzer = sweep_analyzer
        self._bms_detector = BMSDetector(smc_config)
        self._choch_detector = CHOCHDetector(smc_config)
        self._inducement_detector = InducementDetector(smc_config)
        self._fvg_detector = FVGDetector(smc_config, candle_analyzer)
        self._logger = get_logger(__name__)

    async def confirm(
        self,
        request: LTFConfirmationRequest,
        broker_client: BrokerBase,
    ) -> LTFConfirmationResponse:
        """Run the two-layer confirmation pipeline."""
        start = datetime.now(UTC)
        symbol = request.symbol
        direction = Direction(request.direction)
        ltf_tf = Timeframe(request.ltf_timeframe)

        self._logger.info(
            "ltf_confirmation_service_started",
            extra={
                "symbol": symbol,
                "direction": request.direction,
                "ltf_timeframe": request.ltf_timeframe,
                "ob_upper": request.ob_upper,
                "ob_lower": request.ob_lower,
                "entry_price": request.entry_price,
                "stop_loss": request.stop_loss,
                "htf_timeframe": request.htf_timeframe,
                "trace_id": request.trace_id,
            },
        )

        try:
            # ---------------------------------------------------------------
            # Layer 1: HTF Invalidation Check
            # ---------------------------------------------------------------
            # Resolve the HTF timeframe: explicit > derived from LTF parent.
            htf_tf = self._resolve_htf_timeframe(request.htf_timeframe, ltf_tf)

            if htf_tf is not None:
                invalidation = await self._run_invalidation_layer(
                    symbol=symbol,
                    direction=direction,
                    htf_tf=htf_tf,
                    ob_upper=request.ob_upper,
                    ob_lower=request.ob_lower,
                    stop_loss=request.stop_loss,
                    broker_client=broker_client,
                    trace_id=request.trace_id,
                )

                if invalidation["invalidated"]:
                    elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
                    reason = invalidation["reason"]

                    self._logger.warning(
                        "ltf_confirmation_setup_invalidated",
                        extra={
                            "symbol": symbol,
                            "direction": request.direction,
                            "reason": reason,
                            "invalidation_checks": invalidation["checks"],
                            "duration_ms": elapsed,
                            "trace_id": request.trace_id,
                        },
                    )

                    return LTFConfirmationResponse(
                        confirmed=False,
                        symbol=symbol,
                        direction=request.direction,
                        ltf_timeframe=request.ltf_timeframe,
                        checks={},
                        duration_ms=elapsed,
                        invalidated=True,
                        invalidation_reason=reason,
                        invalidation_checks=invalidation["checks"],
                    )

                self._logger.info(
                    "ltf_confirmation_invalidation_passed",
                    extra={
                        "symbol": symbol,
                        "invalidation_checks": invalidation["checks"],
                        "trace_id": request.trace_id,
                    },
                )

            # ---------------------------------------------------------------
            # Layer 2: LTF Confirmation Check
            # ---------------------------------------------------------------
            sequence = await self._fetch_candles(
                symbol, ltf_tf, broker_client, self.LTF_LOOKBACK,
            )
            if sequence is None or sequence.count < 10:
                elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
                return LTFConfirmationResponse(
                    confirmed=False,
                    symbol=symbol,
                    direction=request.direction,
                    ltf_timeframe=request.ltf_timeframe,
                    checks={},
                    duration_ms=elapsed,
                    error="Insufficient LTF candle data",
                )

            checks = self._run_ltf_checks(
                sequence, direction, request.ob_upper,
                request.ob_lower, request.entry_price,
            )

            confirmed = all(checks.values())
            elapsed = (datetime.now(UTC) - start).total_seconds() * 1000

            self._logger.info(
                "ltf_confirmation_service_completed",
                extra={
                    "symbol": symbol,
                    "direction": request.direction,
                    "confirmed": confirmed,
                    "checks": checks,
                    "duration_ms": elapsed,
                    "trace_id": request.trace_id,
                },
            )

            return LTFConfirmationResponse(
                confirmed=confirmed,
                symbol=symbol,
                direction=request.direction,
                ltf_timeframe=request.ltf_timeframe,
                checks=checks,
                duration_ms=elapsed,
            )

        except Exception as e:
            elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
            self._logger.error(
                "ltf_confirmation_service_failed",
                extra={
                    "symbol": symbol,
                    "error": str(e),
                    "trace_id": request.trace_id,
                },
                exc_info=True,
            )
            return LTFConfirmationResponse(
                confirmed=False,
                symbol=symbol,
                direction=request.direction,
                ltf_timeframe=request.ltf_timeframe,
                checks={},
                duration_ms=elapsed,
                error=str(e),
            )

    # -------------------------------------------------------------------
    # Layer 1: HTF Invalidation
    # -------------------------------------------------------------------

    def _resolve_htf_timeframe(
        self,
        explicit_htf: Optional[str],
        ltf: Timeframe,
    ) -> Optional[Timeframe]:
        """Resolve the HTF timeframe for invalidation checks.

        Priority:
          1. Explicit htf_timeframe from the request (the timeframe
             the OB was originally detected on).
          2. Derived: one parent step above the LTF using the
             timeframe hierarchy (M5 -> M15, M15 -> H1, etc.).
          3. None if derivation fails (e.g., LTF is already MN1).
        """
        if explicit_htf:
            try:
                return Timeframe(explicit_htf)
            except ValueError:
                self._logger.warning(
                    "invalid_explicit_htf_timeframe",
                    extra={"htf_timeframe": explicit_htf},
                )

        # Derive: go 2 steps up from LTF to get the HTF where the OB lives.
        # M5 -> M30 (skip M15), M15 -> H1 (skip M30), etc.
        # If 2 steps fails, try 1 step.
        parent = get_parent_timeframe(ltf, steps=2)
        if parent is not None:
            return parent

        parent = get_parent_timeframe(ltf, steps=1)
        return parent

    async def _run_invalidation_layer(
        self,
        symbol: str,
        direction: Direction,
        htf_tf: Timeframe,
        ob_upper: float,
        ob_lower: float,
        stop_loss: Optional[float],
        broker_client: BrokerBase,
        trace_id: Optional[str],
    ) -> dict:
        """Run HTF invalidation checks against the exact approved candidate.

        Returns:
            {
                "invalidated": bool,
                "reason": str or None,
                "checks": {
                    "ob_still_fresh": bool,
                    "no_opposing_bms": bool,
                    "sl_not_blown": bool,
                },
            }
        """
        sequence = await self._fetch_candles(
            symbol, htf_tf, broker_client, self.HTF_LOOKBACK,
        )

        if sequence is None or sequence.count < 5:
            # Cannot validate -> assume still valid (fail-open).
            # Better to attempt the trade than to block it because
            # we couldn't fetch HTF candles.
            self._logger.warning(
                "htf_invalidation_insufficient_data_failing_open",
                extra={
                    "symbol": symbol,
                    "htf_timeframe": htf_tf,
                    "trace_id": trace_id,
                },
            )
            return {
                "invalidated": False,
                "reason": None,
                "checks": {
                    "ob_still_fresh": True,
                    "no_opposing_bms": True,
                    "sl_not_blown": True,
                },
            }

        # Check 1: OB body mitigation.
        # Has a candle BODY closed through the exact OB zone?
        # A wick into the zone is the RTO entry opportunity, NOT invalidation.
        # True mitigation = candle body overlap with the zone exceeds the
        # configured threshold (default 50%).
        ob_fresh = self._check_ob_still_fresh(
            sequence, direction, ob_upper, ob_lower,
        )

        # Check 2: Opposing BMS.
        # Has a new BMS formed in the OPPOSITE direction to the approved trade?
        # BULLISH trade -> check for BEARISH BMS (bearish breaks swing lows).
        # BEARISH trade -> check for BULLISH BMS (bullish breaks swing highs).
        no_opposing_bms = self._check_no_opposing_bms(
            sequence, direction,
        )

        # Check 3: Stop loss blown.
        # Has price already closed beyond the approved candidate's SL?
        sl_not_blown = self._check_sl_not_blown(
            sequence, direction, stop_loss,
        )

        checks = {
            "ob_still_fresh": ob_fresh,
            "no_opposing_bms": no_opposing_bms,
            "sl_not_blown": sl_not_blown,
        }

        # Determine invalidation reason (first failure wins).
        if not ob_fresh:
            return {
                "invalidated": True,
                "reason": f"OB zone ({ob_lower:.5f}-{ob_upper:.5f}) has been body-mitigated on {htf_tf}",
                "checks": checks,
            }

        if not no_opposing_bms:
            opposing = "BEARISH" if direction == Direction.BULLISH else "BULLISH"
            return {
                "invalidated": True,
                "reason": f"New {opposing} BMS detected on {htf_tf}, breaking the {direction} structure",
                "checks": checks,
            }

        if not sl_not_blown:
            return {
                "invalidated": True,
                "reason": f"Price has already closed beyond stop loss ({stop_loss:.5f}) on {htf_tf}",
                "checks": checks,
            }

        return {
            "invalidated": False,
            "reason": None,
            "checks": checks,
        }

    def _check_ob_still_fresh(
        self,
        sequence: CandleSequence,
        direction: Direction,
        ob_upper: float,
        ob_lower: float,
    ) -> bool:
        """Check if the exact OB zone is still fresh (unmitigated).

        Enforces the framework's authoritative close-beyond-extreme
        rule, identical to ``ZoneValidator.validate_zone_freshness``
        which is the single source of truth for mitigation across the
        entire system (also used by the TA orchestrator's OB pass):

          - Bullish OB (demand): invalid as soon as any candle CLOSES
            strictly below ``ob_lower``.
          - Bearish OB (supply): invalid as soon as any candle CLOSES
            strictly above ``ob_upper``.

        This is a wick-tolerant test on purpose.  A candle that wicks
        into the OB but closes back outside is the RTO leg itself --
        the exact entry opportunity this confirmation pulse looks for.
        Only a CLOSE beyond the extreme counts as mitigation, per
        SMC-MS-003 / SMC-MS-004 / SMC-OB-004 / SMC-MIT-001 /
        SMC-INV-005.

        No body-percentage threshold is applied: the framework defines
        mitigation in binary close-beyond terms, and SMCConfig
        deliberately exposes no body-threshold knob (see config.py).

        Returns True if the OB is still fresh (NOT mitigated).
        """
        if ob_upper - ob_lower <= 0:
            return True  # Invalid zone data, fail-open.

        for candle in sequence.candles:
            if direction == Direction.BULLISH:
                # Bullish OB (demand): mitigated once price CLOSES
                # completely below the zone's low.
                if candle.close < ob_lower:
                    return False
            elif direction == Direction.BEARISH:
                # Bearish OB (supply): mitigated once price CLOSES
                # completely above the zone's high.
                if candle.close > ob_upper:
                    return False

        return True  # No candle closed beyond the zone extreme.

    def _check_no_opposing_bms(
        self,
        sequence: CandleSequence,
        direction: Direction,
    ) -> bool:
        """Check that no opposing BMS has formed on the HTF.

        For a BULLISH approved trade: check for new BEARISH BMS
        (price broke below a swing low with displacement).

        For a BEARISH approved trade: check for new BULLISH BMS
        (price broke above a swing high with displacement).

        We only care about RECENT opposing BMS (last ~20 candles)
        to avoid flagging old structure breaks from before the
        original analysis.

        Returns True if NO opposing BMS was found (setup still valid).
        """
        # Only scan the most recent portion of the sequence.
        # The original analysis already accounted for older structure.
        recency_window = min(20, len(sequence.candles))
        recent_candles = sequence.candles[-recency_window:]

        # Build a sub-sequence for the recent window.
        # We need to detect swings and BMS only in this window.
        swing_highs = self._swing_analyzer.detect_swing_highs(sequence)
        swing_lows = self._swing_analyzer.detect_swing_lows(sequence)

        if direction == Direction.BULLISH:
            # Check for BEARISH BMS (opposing to our bullish trade).
            opposing_bms = self._bms_detector.detect_bearish_bms(
                sequence, swing_lows,
            )
            # Only count BMS events that occurred in the recent window.
            if recent_candles:
                recent_start_ts = recent_candles[0].timestamp
                opposing_bms = [
                    bms for bms in opposing_bms
                    if bms.timestamp >= recent_start_ts
                ]
        else:
            # Check for BULLISH BMS (opposing to our bearish trade).
            opposing_bms = self._bms_detector.detect_bullish_bms(
                sequence, swing_highs,
            )
            if recent_candles:
                recent_start_ts = recent_candles[0].timestamp
                opposing_bms = [
                    bms for bms in opposing_bms
                    if bms.timestamp >= recent_start_ts
                ]

        if opposing_bms:
            latest = max(opposing_bms, key=lambda b: b.timestamp)
            self._logger.info(
                "opposing_bms_detected",
                extra={
                    "direction": direction,
                    "opposing_direction": latest.direction,
                    "broken_level": latest.broken_level,
                    "displacement_pips": latest.displacement_pips,
                    "timestamp": latest.timestamp.isoformat(),
                },
            )
            return False

        return True

    def _check_sl_not_blown(
        self,
        sequence: CandleSequence,
        direction: Direction,
        stop_loss: Optional[float],
    ) -> bool:
        """Check that price has not closed beyond the stop loss.

        For BULLISH: SL is below entry. Blown if candle CLOSES below SL.
        For BEARISH: SL is above entry. Blown if candle CLOSES above SL.

        Uses candle close (not wick) because a wick through SL that
        closes back inside is a sweep, not a true SL hit.

        Returns True if SL has NOT been blown.
        """
        if stop_loss is None or stop_loss <= 0:
            return True  # No SL provided, skip check.

        # Only check the most recent candles (last 10).
        # Older candles predate the watcher arming.
        recent = sequence.candles[-10:] if len(sequence.candles) > 10 else sequence.candles

        for candle in recent:
            if direction == Direction.BULLISH:
                if candle.close < stop_loss:
                    return False
            elif direction == Direction.BEARISH:
                if candle.close > stop_loss:
                    return False

        return True

    # -------------------------------------------------------------------
    # Layer 2: LTF Confirmation
    # -------------------------------------------------------------------

    def _run_ltf_checks(
        self,
        sequence: CandleSequence,
        direction: Direction,
        ob_upper: float,
        ob_lower: float,
        entry_price: float,
    ) -> dict:
        """Run all 7 LTF confirmation checks and return individual results."""
        swing_highs = self._swing_analyzer.detect_swing_highs(sequence)
        swing_lows = self._swing_analyzer.detect_swing_lows(sequence)

        if direction == Direction.BULLISH:
            bms_events = self._bms_detector.detect_bullish_bms(sequence, swing_highs)
            choch_events = self._choch_detector.detect_bullish_choch(sequence, swing_highs)
            inducements = self._inducement_detector.detect_bullish_inducement(sequence, swing_lows)
        else:
            bms_events = self._bms_detector.detect_bearish_bms(sequence, swing_lows)
            choch_events = self._choch_detector.detect_bearish_choch(sequence, swing_lows)
            inducements = self._inducement_detector.detect_bearish_inducement(sequence, swing_highs)

        sweeps = self._sweep_analyzer.detect_sweeps_in_sequence(
            sequence, swing_highs, swing_lows,
        )
        fvgs = self._fvg_detector.detect_fvgs(sequence)

        current_price = sequence.candles[-1].close
        latest_candle = sequence.candles[-1]

        # Check 1: Liquidity sweep taken
        sweep_ok = False
        for sweep in sweeps:
            if sweep.closed_back_inside:
                sweep_ok = True
                break

        # Check 2: CHOCH present
        choch_ok = len(choch_events) > 0

        # Check 3: BMS confirmed
        bms_ok = len(bms_events) > 0

        # Check 4: RTO - current price inside the OB zone
        rto_ok = ob_lower <= current_price <= ob_upper

        # Check 5: Session timing
        session_state = self._session_analyzer.identify_session(
            latest_candle.timestamp,
        )
        valid_sessions = [Session.LONDON, Session.NEW_YORK, Session.OVERLAP_LONDON_NY]
        session_ok = session_state.active_session in valid_sessions
        if not self._config.require_session_timing:
            session_ok = True

        # Check 6: Inducement cleared
        inducement_ok = True
        relevant_inducements = [
            idm for idm in inducements
            if idm.direction == direction
        ]
        if relevant_inducements:
            inducement_ok = all(idm.cleared for idm in relevant_inducements)

        # Check 7: FVG present aligned with direction
        fvg_ok = any(fvg.direction == direction for fvg in fvgs)

        return {
            "liquidity_swept": sweep_ok,
            "choch_present": choch_ok,
            "bms_confirmed": bms_ok,
            "rto_to_ob": rto_ok,
            "session_timing": session_ok,
            "inducement_cleared": inducement_ok,
            "fvg_present": fvg_ok,
        }

    # -------------------------------------------------------------------
    # Shared: Candle Fetching
    # -------------------------------------------------------------------

    async def _fetch_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        broker: BrokerBase,
        lookback: int,
    ) -> Optional[CandleSequence]:
        """Fetch candles for a single timeframe."""
        end_time = datetime.now(UTC)
        minutes = TIMEFRAME_MINUTES.get(timeframe, 5)
        start_time = end_time - timedelta(minutes=minutes * lookback)

        try:
            sequence = await broker.fetch_candles(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
                count=lookback,
            )
            return sequence
        except Exception as e:
            self._logger.error(
                "candle_fetch_failed",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "lookback": lookback,
                    "error": str(e),
                },
            )
            return None
