from engine.shared.logging import get_logger
from engine.ta.common.analyzers.dealing_range import DealingRangeAnalyzer
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.analyzers.liquidity import LiquidityAnalyzer
from engine.ta.common.analyzers.session import SessionAnalyzer
from engine.ta.common.analyzers.sweeps import SweepAnalyzer
from engine.ta.common.analyzers.swings import SwingAnalyzer
from engine.ta.constants import Direction
from engine.ta.models.candidate import TechnicalCandidate
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import DealingRange, FibonacciRetracement
from engine.ta.models.liquidity_event import (
    EqualHighsLows,
    InducementEvent,
    LiquidityGrab,
    LiquiditySweep,
)
from engine.ta.models.snapshot import TechnicalSnapshot
from engine.ta.models.structure_event import (
    BreakInMarketStructure,
    BreakOfStructure,
    ChangeOfCharacter,
    RSFlip,
    ShiftInMarketStructure,
    SRFlip,
)
from engine.ta.models.zone import (
    BreakerBlock,
    DemandZone,
    FairValueGap,
    MiniPriceLevel,
    OrderBlock,
    QuasiModoLevel,
    SupplyZone,
)

logger = get_logger(__name__)


class SnapshotBuilder:
    def __init__(
        self,
        swing_analyzer: SwingAnalyzer,
        session_analyzer: SessionAnalyzer,
        liquidity_analyzer: LiquidityAnalyzer,
        sweep_analyzer: SweepAnalyzer,
        fibonacci_analyzer: FibonacciAnalyzer,
        dealing_range_analyzer: DealingRangeAnalyzer,
    ) -> None:
        self.swing_analyzer = swing_analyzer
        self.session_analyzer = session_analyzer
        self.liquidity_analyzer = liquidity_analyzer
        self.sweep_analyzer = sweep_analyzer
        self.fibonacci_analyzer = fibonacci_analyzer
        self.dealing_range_analyzer = dealing_range_analyzer
        self._logger = get_logger(__name__)

    def build_snapshot(
        self,
        candles: CandleSequence,
        bos_events: list[BreakOfStructure] | None = None,
        choch_events: list[ChangeOfCharacter] | None = None,
        bms_events: list[BreakInMarketStructure] | None = None,
        sms_events: list[ShiftInMarketStructure] | None = None,
        sr_flips: list[SRFlip] | None = None,
        rs_flips: list[RSFlip] | None = None,
        liquidity_sweeps: list[LiquiditySweep] | None = None,
        liquidity_grabs: list[LiquidityGrab] | None = None,
        inducement_events: list[InducementEvent] | None = None,
        equal_highs_lows: list[EqualHighsLows] | None = None,
        order_blocks: list[OrderBlock] | None = None,
        fvgs: list[FairValueGap] | None = None,
        breaker_blocks: list[BreakerBlock] | None = None,
        supply_zones: list[SupplyZone] | None = None,
        demand_zones: list[DemandZone] | None = None,
        qml_levels: list[QuasiModoLevel] | None = None,
        mpl_levels: list[MiniPriceLevel] | None = None,
        fibonacci_retracements: list[FibonacciRetracement] | None = None,
        dealing_ranges: list[DealingRange] | None = None,
        candidates: list[TechnicalCandidate] | None = None,
        metadata: dict | None = None,
    ) -> TechnicalSnapshot:
        swing_highs = self.swing_analyzer.detect_swing_highs(candles)
        swing_lows = self.swing_analyzer.detect_swing_lows(candles)

        latest_candle = candles.candles[-1]
        session_state = self.session_analyzer.identify_session(latest_candle.timestamp)

        trend_direction = self._determine_trend_direction(
            candles=candles,
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            bms_events=bms_events or [],
            choch_events=choch_events or [],
        )

        snapshot = TechnicalSnapshot(
            symbol=candles.symbol,
            timeframe=candles.timeframe,
            timestamp=latest_candle.timestamp,
            candles=candles,
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            bos_events=bos_events or [],
            choch_events=choch_events or [],
            bms_events=bms_events or [],
            sms_events=sms_events or [],
            sr_flips=sr_flips or [],
            rs_flips=rs_flips or [],
            liquidity_sweeps=liquidity_sweeps or [],
            liquidity_grabs=liquidity_grabs or [],
            inducement_events=inducement_events or [],
            equal_highs_lows=equal_highs_lows or [],
            order_blocks=order_blocks or [],
            fvgs=fvgs or [],
            breaker_blocks=breaker_blocks or [],
            supply_zones=supply_zones or [],
            demand_zones=demand_zones or [],
            qml_levels=qml_levels or [],
            mpl_levels=mpl_levels or [],
            fibonacci_retracements=fibonacci_retracements or [],
            dealing_ranges=dealing_ranges or [],
            session_state=session_state,
            trend_direction=trend_direction,
            candidates=candidates or [],
            metadata=metadata or {},
        )

        self._logger.info(
            "snapshot_built",
            extra={
                "symbol": candles.symbol,
                "timeframe": candles.timeframe,
                "candle_count": candles.count,
                "swing_highs": len(swing_highs),
                "swing_lows": len(swing_lows),
                "total_structure_events": snapshot.total_structure_events,
                "total_liquidity_events": snapshot.total_liquidity_events,
                "total_zones": snapshot.total_zones,
                "total_candidates": snapshot.total_candidates,
                "trend_direction": trend_direction,
            },
        )

        return snapshot

    def _determine_trend_direction(
        self,
        candles: CandleSequence,
        swing_highs: list,
        swing_lows: list,
        bms_events: list[BreakInMarketStructure],
        choch_events: list[ChangeOfCharacter],
    ) -> Direction:
        """Resolve the trend bias for a single timeframe.

        The logic is layered from the most authoritative source of
        truth to the most permissive, and the first layer that can
        reach a decision wins:

        1. Confirmed BMS / major CHoCH.  These are the SMC-defined
           structural breaks; once they fire they dictate bias until
           a newer break in the opposite direction fires.  Minor
           CHoCHs (internal-structure breaks) are excluded because
           they describe pullbacks within a larger leg, not a macro
           flip.

        2. In-flight momentum on the forming candle.  BMS requires
           2 / 3 / 5 consecutive confirmation closes (per
           BMSDetector._required_confirmation_candles) and swing
           detection requires ``right_bars`` additional bars after
           the swing.  During the current forming HTF candle those
           requirements cannot yet be satisfied even when price has
           unambiguously traded through every prior confirmed
           extreme.  When the latest close is strictly above the
           highest confirmed swing high (or strictly below the
           lowest confirmed swing low) the break is unambiguous
           regardless of confirmation, so the bias flips now.  This
           closes the USTEC-W1-style blind spot without ever
           contradicting a confirmed event from layer 1.

        3. Strict monotonic HH / LL on the last three confirmed
           swings (unchanged legacy behaviour, now reached only
           when layers 1 and 2 cannot decide).

        4. Premium / discount relative to the full swing range.
           When a symbol has valid swings but no confirmed break,
           no in-flight break, and no monotonic sequence, bias is
           taken from the side of equilibrium the latest close sits
           on.  This aligns with the dealing-range premium /
           discount model used elsewhere in the TA stack and
           eliminates spurious NEUTRAL readings that used to leak
           through alignment and overall-trend downstream.

        The only remaining NEUTRAL path is the "no swings" data
        integrity guard at the top.  A symbol without swings has
        nothing to analyse and should not be given a fabricated
        direction.
        """
        if not swing_highs or not swing_lows:
            return Direction.NEUTRAL

        # Layer 1: confirmed BMS / major CHoCH.
        latest_bms = max(bms_events, key=lambda x: x.timestamp) if bms_events else None
        # Only MAJOR CHoCH events flip macro bias; minor CHoCH events
        # describe internal pullbacks, not a structural reversal.
        major_choch_events = [c for c in choch_events if not getattr(c, "is_minor", False)]
        latest_choch = max(major_choch_events, key=lambda x: x.timestamp) if major_choch_events else None

        if latest_bms and latest_choch:
            if latest_bms.timestamp > latest_choch.timestamp:
                return latest_bms.direction
            return latest_choch.direction
        if latest_bms:
            return latest_bms.direction
        if latest_choch:
            return latest_choch.direction

        # Layer 2: in-flight momentum on the forming candle.
        # Uses the extremes of every confirmed swing (not just the
        # most recent) so a partial break above the newest swing
        # high but still below an older higher swing high does NOT
        # count as bullish.  A break here is unambiguous by
        # construction.
        latest_close: float | None = None
        if candles is not None and candles.candles:
            latest_close = candles.candles[-1].close

        highest_swing_high = max(sh.price for sh in swing_highs)
        lowest_swing_low = min(sl.price for sl in swing_lows)

        if latest_close is not None:
            if latest_close > highest_swing_high:
                return Direction.BULLISH
            if latest_close < lowest_swing_low:
                return Direction.BEARISH

        # Layer 3: strict monotonic HH / LL on the last three swings.
        recent_highs = sorted(swing_highs, key=lambda x: x.timestamp)[-3:]
        recent_lows = sorted(swing_lows, key=lambda x: x.timestamp)[-3:]

        if len(recent_highs) >= 2:
            higher_highs = all(recent_highs[i].price > recent_highs[i - 1].price for i in range(1, len(recent_highs)))
            if higher_highs:
                return Direction.BULLISH

        if len(recent_lows) >= 2:
            lower_lows = all(recent_lows[i].price < recent_lows[i - 1].price for i in range(1, len(recent_lows)))
            if lower_lows:
                return Direction.BEARISH

        # Layer 4: premium / discount equilibrium fallback.
        # Only reached when no confirmed break, no in-flight break,
        # and no monotonic sequence exists.  Uses the latest close
        # relative to the swing-range midpoint, matching the
        # DealingRange equilibrium model used elsewhere.
        if latest_close is not None:
            equilibrium = (highest_swing_high + lowest_swing_low) / 2.0
            if latest_close >= equilibrium:
                return Direction.BULLISH
            return Direction.BEARISH

        # Final safety net: without a latest close we cannot score
        # premium / discount either.  Preserve NEUTRAL only in this
        # degenerate, data-incomplete case.
        return Direction.NEUTRAL
