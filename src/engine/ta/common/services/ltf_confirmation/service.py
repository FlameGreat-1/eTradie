"""Lightweight LTF confirmation service.

Designed for the execution watcher's fast-path confirmation pulse.
Fetches only LTF candle data and runs only the 7 SMC LTF confirmation
checks. Returns in milliseconds, not seconds.

This replaces the full TA pipeline re-run that the Gateway previously
used for confirmation pulses.
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
from engine.ta.constants import Direction, Session, Timeframe, TIMEFRAME_MINUTES
from engine.ta.models.candle import CandleSequence
from engine.ta.models.zone import OrderBlock
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


class LTFConfirmationResponse(BaseModel):
    """Response from the lightweight LTF confirmation check."""
    confirmed: bool
    symbol: str
    direction: str
    ltf_timeframe: str
    checks: dict  # Individual check results
    duration_ms: float
    error: Optional[str] = None


class LTFConfirmationService:
    """Lightweight LTF-only confirmation for execution watchers.

    Fetches only the LTF candle data and runs only the checks needed
    to determine if LTF confirmation exists at the current moment:

    1. Liquidity sweep (SSL/BSL taken and closed back inside)
    2. CHOCH on LTF (change of character)
    3. BMS on LTF (break in market structure)
    4. RTO to OB (current price inside the Order Block zone)
    5. Session timing (London/NY active)
    6. Inducement cleared
    7. FVG present on LTF

    All 7 must be True for confirmed=True (instant order fire).
    Individual results are returned so the watcher knows what's missing.
    """

    # Number of LTF candles to fetch. Enough for structural detection
    # but small enough to be fast.
    LTF_LOOKBACK = 150

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
        """Run lightweight LTF confirmation checks."""
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
                "trace_id": request.trace_id,
            },
        )

        try:
            # Fetch ONLY the LTF candle data
            sequence = await self._fetch_ltf_candles(
                symbol, ltf_tf, broker_client,
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

            # Run structural detection on LTF only
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

    async def _fetch_ltf_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        broker: BrokerBase,
    ) -> Optional[CandleSequence]:
        """Fetch only the LTF candles needed for confirmation."""
        end_time = datetime.now(UTC)
        minutes = TIMEFRAME_MINUTES.get(timeframe, 5)
        start_time = end_time - timedelta(minutes=minutes * self.LTF_LOOKBACK)

        try:
            sequence = await broker.fetch_candles(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
                count=self.LTF_LOOKBACK,
            )
            return sequence
        except Exception as e:
            self._logger.error(
                "ltf_candle_fetch_failed",
                extra={"symbol": symbol, "timeframe": timeframe, "error": str(e)},
            )
            return None

    def _run_ltf_checks(
        self,
        sequence: CandleSequence,
        direction: Direction,
        ob_upper: float,
        ob_lower: float,
        entry_price: float,
    ) -> dict:
        """Run all 7 LTF confirmation checks and return individual results."""
        # Detect structural elements on LTF
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
        inducement_ok = True  # Default: no inducement = OK
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
