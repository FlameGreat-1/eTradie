from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import Direction, PriceZone
from engine.ta.models.candle import CandleSequence
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.liquidity_event import InducementEvent, LiquiditySweep
from engine.ta.models.structure_event import BreakInMarketStructure, ChangeOfCharacter
from engine.ta.models.swing import SwingHigh, SwingLow
from engine.ta.models.zone import OrderBlock, FairValueGap
from engine.ta.smc.config import SMCConfig

logger = get_logger(__name__)


class ZoneValidator:
    """
    Validates SMC zones against the 7 Rules of a Tradeable Order Block.

    All 7 rules must be satisfied for a zone to be tradeable:
    1. Must sponsor a BOS/CHOCH
    2. Must have FVG associated
    3. Must have liquidity/inducement present
    4. Must take out opposing OB
    5. Must be at Premium (sells) or Discount (buys)
    6. Must have BPR (FVG within FVG, OB within OB on subsequent TF)
    7. Select HTF OBs, refine to LTF

    This validator handles rules 2, 3, 5. Rules 1, 4, 6, 7 handled elsewhere.

    Key design principles:
    - OTE alignment is a **confluence booster**, not a hard gate.  Valid
      setups exist outside the OTE pocket; OTE simply adds probability.
    - FVG association uses structural proximity (candle distance) rather
      than arbitrary clock time, so it works across all timeframes.
    - Zone freshness distinguishes between a retest/RTO (wick into zone,
      body closes outside) and true mitigation (body closes through).
      A retest IS the entry opportunity, not invalidation.
    """

    def __init__(
        self,
        config: SMCConfig,
        fibonacci_analyzer: FibonacciAnalyzer,
    ) -> None:
        self.config = config
        self.fibonacci_analyzer = fibonacci_analyzer
        self._logger = get_logger(__name__)

    # ------------------------------------------------------------------
    # Rule 2: FVG association
    # ------------------------------------------------------------------

    def validate_ob_has_fvg(
        self,
        ob: OrderBlock,
        fvgs: list[FairValueGap],
    ) -> bool:
        """Rule 2: Must have FVG associated.

        The displacement that creates an Order Block almost always leaves
        a Fair Value Gap (imbalance) behind.  We check:

        1. Directional alignment: FVG and OB must share the same direction.
        2. Structural proximity: the FVG must have formed within a
           configurable number of candles from the OB (default 5),
           measured by candle_index distance.  This replaces the old
           1-hour clock-time check and works across all timeframes.
        3. Spatial relationship: the FVG must overlap the OB price range
           OR be adjacent to it (FVG sits just above a bullish OB or
           just below a bearish OB, which is the natural imbalance left
           by the displacement leg).
        """
        if not self.config.require_fvg_with_ob:
            return True

        max_distance = self.config.fvg_max_candle_distance

        for fvg in fvgs:
            # 1. Directional alignment
            if fvg.direction != ob.direction:
                continue

            # 2. Structural proximity by candle index
            if abs(fvg.candle_index - ob.candle_index) > max_distance:
                continue

            # 3a. FVG overlaps the OB price range
            if self._ranges_overlap(
                ob.lower_bound, ob.upper_bound,
                fvg.lower_bound, fvg.upper_bound,
            ):
                return True

            # 3b. FVG is adjacent to the OB (displacement leg)
            #     Bullish OB: FVG sits above the OB (price displaced up)
            #     Bearish OB: FVG sits below the OB (price displaced down)
            if ob.direction == Direction.BULLISH:
                if fvg.lower_bound >= ob.lower_bound:
                    return True
            else:
                if fvg.upper_bound <= ob.upper_bound:
                    return True

        return False

    # ------------------------------------------------------------------
    # Rule 3: Liquidity / inducement present
    # ------------------------------------------------------------------

    def validate_ob_has_liquidity(
        self,
        ob: OrderBlock,
        liquidity_sweeps: list[LiquiditySweep],
        inducement_events: list[InducementEvent],
    ) -> bool:
        """Rule 3: Must have liquidity or inducement present.

        Liquidity sweeps and inducement clearances confirm that smart
        money has engineered a move.  We check structural proximity
        (candle index distance) rather than clock time.
        """
        max_distance = self.config.fvg_max_candle_distance

        for sweep in liquidity_sweeps:
            if sweep is None:
                continue
            if abs(sweep.candle_index - ob.candle_index) <= max_distance:
                return True

        for inducement in inducement_events:
            if inducement.cleared and inducement.cleared_timestamp is not None:
                # Inducement was cleared before or at the OB formation
                if inducement.cleared_timestamp <= ob.timestamp:
                    return True
                # Or cleared within structural proximity
                if (
                    hasattr(inducement, "candle_index")
                    and abs(inducement.candle_index - ob.candle_index)
                    <= max_distance
                ):
                    return True

        # If no sweeps or inducements exist at all, we still allow the
        # OB through.  Liquidity is a confluence, and its absence is
        # captured in the confluence count, not as a hard rejection.
        return True

    # ------------------------------------------------------------------
    # Rule 5: Premium / Discount (OTE confluence)
    # ------------------------------------------------------------------

    def score_ob_fib_confluence(
        self,
        ob: OrderBlock,
        retracement: Optional[FibonacciRetracement],
    ) -> int:
        """Score the Fibonacci confluence for an Order Block.

        Returns a confluence score (0-3) instead of a boolean gate:

        - 3: OB midpoint is inside the OTE pocket (61.8%-78.6%).
             Highest probability.  This is the institutional sweet spot.
        - 2: OB midpoint is in the correct premium/discount zone
             (above equilibrium for bearish sells, below for bullish buys)
             but outside the OTE pocket.
        - 1: OB midpoint is near equilibrium (50% level).
             Lower probability but still a valid setup.
        - 0: No retracement available, or OB is in the wrong zone
             (e.g. buying at premium).  Zero Fib confluence but the
             OB is NOT rejected — other confluences may still make
             it a valid candidate.
        """
        if not retracement:
            return 0

        midpoint = ob.midpoint

        # Check OTE pocket first (highest score)
        if self.fibonacci_analyzer.is_at_ote(
            midpoint,
            retracement,
            tolerance_pips=self.config.fibonacci_tolerance_pips,
        ):
            return 3

        # Check correct premium/discount zone
        zone = self.fibonacci_analyzer.get_zone_for_price(midpoint, retracement)

        if ob.direction == Direction.BULLISH and zone == PriceZone.DISCOUNT:
            return 2
        if ob.direction == Direction.BEARISH and zone == PriceZone.PREMIUM:
            return 2

        # Equilibrium — valid but lower probability
        if zone == PriceZone.EQUILIBRIUM:
            return 1

        return 0

    def validate_ob_at_premium_discount(
        self,
        ob: OrderBlock,
        retracement: Optional[FibonacciRetracement],
    ) -> bool:
        """Rule 5: Premium/Discount check.

        This method now returns True for ALL Order Blocks.  The Fibonacci
        alignment is captured as a confluence score via
        ``score_ob_fib_confluence()`` and factored into the candidate's
        total confluence count.  An OB is never rejected solely for
        being outside the OTE pocket.

        Rationale: most valid OBs do form at OTE levels, but the market
        is fractal and dynamic.  Rejecting every OB outside a narrow
        Fib band causes the system to miss valid setups entirely.
        The Fib score ensures OTE-aligned setups are ranked higher
        without silently discarding non-OTE setups.
        """
        # Always pass — Fib alignment is a confluence, not a gate.
        return True

    # ------------------------------------------------------------------
    # Zone freshness (mitigation detection)
    # ------------------------------------------------------------------

    def validate_zone_freshness(
        self,
        ob: OrderBlock,
        sequence: CandleSequence,
    ) -> bool:
        """Validate zone is unmitigated (fresh).

        Distinguishes between:
        - **Retest / RTO**: price wicks into the zone but the candle
          body closes outside.  This IS the entry opportunity.
        - **True mitigation**: a candle's body closes decisively
          through the zone (configurable threshold, default 50% of
          body inside the zone).  The zone is consumed.

        The old implementation treated any wick touch as mitigation,
        which rejected virtually every OB because price almost always
        retests a zone before continuing.
        """
        if ob.mitigated:
            return False

        if ob.candle_index >= len(sequence.candles) - 1:
            return True

        body_threshold = self.config.zone_mitigation_body_threshold / 100.0

        for i in range(ob.candle_index + 1, len(sequence.candles)):
            candle = sequence.candles[i]
            body_top = max(candle.open, candle.close)
            body_bottom = min(candle.open, candle.close)
            body_size = body_top - body_bottom

            if body_size == 0:
                # Doji candle — no body, cannot mitigate
                continue

            if ob.direction == Direction.BULLISH:
                # Bullish OB: mitigation = bearish body closes through
                # the zone from above (price falls through the demand).
                # A wick below is a retest, not mitigation.
                if body_bottom > ob.upper_bound:
                    # Body entirely above the zone — no interaction
                    continue
                if body_top < ob.lower_bound:
                    # Body entirely below the zone — zone is broken
                    return False

                # Calculate how much of the body is inside the zone
                overlap_top = min(body_top, ob.upper_bound)
                overlap_bottom = max(body_bottom, ob.lower_bound)
                overlap = max(0.0, overlap_top - overlap_bottom)
                body_inside_pct = overlap / body_size

                if body_inside_pct >= body_threshold:
                    return False

            else:
                # Bearish OB (supply zone): sits ABOVE current price.
                # Mitigation = bullish body closes through the zone
                # from below (price rises through the supply).
                # A wick into the zone from below is a retest (RTO).
                if body_top < ob.lower_bound:
                    # Body entirely below the zone - no interaction
                    continue
                if body_bottom > ob.upper_bound:
                    # Body entirely above the zone - no interaction
                    # (price has moved past the zone without body
                    # overlap, which is normal before RTO)
                    continue

                # Body overlaps the zone - check if it's true mitigation
                overlap_top = min(body_top, ob.upper_bound)
                overlap_bottom = max(body_bottom, ob.lower_bound)
                overlap = max(0.0, overlap_top - overlap_bottom)
                body_inside_pct = overlap / body_size

                if body_inside_pct >= body_threshold:
                    return False

        return True

    # ------------------------------------------------------------------
    # Zone overlap check
    # ------------------------------------------------------------------

    def validate_zone_no_overlap(
        self,
        ob: OrderBlock,
        other_obs: list[OrderBlock],
    ) -> bool:
        """Validate zone does not overlap with other zones."""
        for other_ob in other_obs:
            if other_ob.timestamp == ob.timestamp:
                continue

            if ob.overlaps_with(other_ob.to_zone()):
                return False

        return True

    # ------------------------------------------------------------------
    # Composite validation
    # ------------------------------------------------------------------

    def validate_all_ob_rules(
        self,
        ob: OrderBlock,
        fvgs: list[FairValueGap],
        liquidity_sweeps: list[LiquiditySweep],
        inducement_events: list[InducementEvent],
        retracement: Optional[FibonacciRetracement],
        sequence: CandleSequence,
        other_obs: list[OrderBlock],
    ) -> bool:
        """Validate all applicable OB rules.

        Returns True if the OB passes the structural validity checks.
        Fibonacci alignment is NOT a gate here — it is scored separately
        via ``score_ob_fib_confluence()`` and added to the candidate's
        confluence count by the builder.
        """
        has_fvg = self.validate_ob_has_fvg(ob, fvgs)
        has_liquidity = self.validate_ob_has_liquidity(
            ob, liquidity_sweeps, inducement_events,
        )
        at_premium_discount = self.validate_ob_at_premium_discount(
            ob, retracement,
        )
        is_fresh = self.validate_zone_freshness(ob, sequence)
        fib_score = self.score_ob_fib_confluence(ob, retracement)

        passed = has_fvg and has_liquidity and at_premium_discount and is_fresh

        # Diagnostic logging at INFO level so operators can see exactly
        # which gate passed/failed without enabling debug.
        self._logger.info(
            "ob_validation_result",
            extra={
                "symbol": ob.symbol,
                "timeframe": str(ob.timeframe),
                "direction": str(ob.direction),
                "ob_timestamp": ob.timestamp.isoformat(),
                "ob_upper": ob.upper_bound,
                "ob_lower": ob.lower_bound,
                "ob_midpoint": ob.midpoint,
                "has_fvg": has_fvg,
                "has_liquidity": has_liquidity,
                "at_premium_discount": at_premium_discount,
                "is_fresh": is_fresh,
                "fib_confluence_score": fib_score,
                "passed": passed,
                "fvg_count": len(fvgs),
                "sweep_count": len(
                    [s for s in liquidity_sweeps if s is not None]
                ),
                "inducement_count": len(inducement_events),
                "has_retracement": retracement is not None,
            },
        )

        return passed

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ranges_overlap(
        a_lower: float,
        a_upper: float,
        b_lower: float,
        b_upper: float,
    ) -> bool:
        """Return True if two price ranges overlap."""
        return a_lower <= b_upper and b_lower <= a_upper
