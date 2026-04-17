from typing import Optional

from engine.shared.logging import get_logger
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import (
    Direction,
    FIBONACCI_VALUES,
    FibonacciLevel,
    PriceZone,
)
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

        return self.get_associated_fvg(ob, fvgs) is not None

    def get_associated_fvg(
        self,
        ob: OrderBlock,
        fvgs: list[FairValueGap],
    ) -> Optional[FairValueGap]:
        """Returns the specific FVG associated with the given Order Block."""
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
                return fvg

            # 3b. FVG is adjacent to the OB
            if ob.direction == Direction.BULLISH:
                if fvg.lower_bound >= ob.lower_bound:
                    return fvg
            else:
                if fvg.upper_bound <= ob.upper_bound:
                    return fvg

        return None

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
    # Inducement selection (direction + geometric relevance to the OB)
    # ------------------------------------------------------------------

    @staticmethod
    def select_relevant_inducement(
        ob: OrderBlock,
        direction: Direction,
        inducement_events: list[InducementEvent],
        bms_breakout_price: Optional[float] = None,
    ) -> Optional[InducementEvent]:
        """Return the single IDM that is geometrically relevant to ``ob``.

        Per SMC-LIQ-004, the IDM a setup must clear is the internal
        liquidity resting on the path between the OB and the
        displacement/BMS that validated the setup:

        - Bullish setups: an SSL (bullish-direction IDM) whose level
          sits above the OB and below the BMS breakout.  Price must
          have swept this SSL before rallying to break structure.
        - Bearish setups: a BSL (bearish-direction IDM) whose level
          sits below the OB and above the BMS breakout.

        Only inducements that were actually ``cleared`` are considered.
        Among qualifying candidates the most recently cleared one
        (by ``cleared_timestamp``) is returned.

        Returns ``None`` when no direction-aligned, geometrically
        relevant, cleared IDM exists.
        """
        candidates: list[InducementEvent] = []

        for idm in inducement_events:
            if not idm.cleared:
                continue
            if idm.direction != direction:
                continue

            level = idm.inducement_level

            if direction == Direction.BULLISH:
                if level < ob.lower_bound:
                    continue
                if bms_breakout_price is not None and level > bms_breakout_price:
                    continue
            else:
                if level > ob.upper_bound:
                    continue
                if bms_breakout_price is not None and level < bms_breakout_price:
                    continue

            candidates.append(idm)

        if not candidates:
            return None

        def _cleared_ts(idm: InducementEvent):
            return idm.cleared_timestamp or idm.inducement_timestamp

        return max(candidates, key=_cleared_ts)

    # ------------------------------------------------------------------
    # Sweep context builder (full liquidity-sweep details for LLM)
    # ------------------------------------------------------------------

    def build_sweep_context(
        self,
        sweep: Optional[LiquiditySweep],
        ob: Optional[OrderBlock] = None,
    ) -> Optional[dict]:
        """Build precise liquidity-sweep context for a candidate.

        A bare ``swept_level`` float is insufficient to reason about a
        sweep: per SMC-LIQ-003 the *type* of liquidity, the *magnitude*
        of the wick, and whether price *closed back inside the range*
        are what qualify a sweep as tradeable.  This helper surfaces
        all of those facts in a single structured dict.

        Parameters
        ----------
        sweep:
            The ``LiquiditySweep`` selected by
            ``SMCDetector._find_relevant_sweep`` for this candidate, or
            ``None`` if no sweep was associated.
        ob:
            Optional OrderBlock whose bounds are used to compute
            ``side_relative_to_ob`` (``"above"`` / ``"below"`` /
            ``"inside"``) — a geometric sanity flag that tells the LLM
            whether the swept level is above the OB (typical for a
            bearish setup where BSL above the OB was taken) or below
            it (typical for a bullish setup where SSL below the OB
            was taken).

        Returns
        -------
        dict | None
            Structured sweep context ready for
            ``SMCCandidate.metadata["sweep_context"]``, or ``None``
            when no sweep is present.
        """
        if sweep is None:
            return None

        is_turtle_soup = bool(
            sweep.closed_back_inside
            and sweep.sweep_pips >= self.config.turtle_soup_min_pips
        )

        side_relative_to_ob: Optional[str] = None
        if ob is not None:
            if sweep.swept_level > ob.upper_bound:
                side_relative_to_ob = "above"
            elif sweep.swept_level < ob.lower_bound:
                side_relative_to_ob = "below"
            else:
                side_relative_to_ob = "inside"

        context: dict = {
            "liquidity_type": sweep.liquidity_type.value,
            "swept_level": sweep.swept_level,
            "swept_level_timestamp": sweep.swept_level_timestamp.isoformat(),
            "sweep_timestamp": sweep.timestamp.isoformat(),
            "sweep_high": sweep.sweep_high,
            "sweep_low": sweep.sweep_low,
            "close_price": sweep.close_price,
            "sweep_pips": round(sweep.sweep_pips, 2),
            "closed_back_inside": sweep.closed_back_inside,
            "is_major_sweep": sweep.is_major_sweep,
            "is_turtle_soup": is_turtle_soup,
            "candle_index": sweep.candle_index,
        }

        if side_relative_to_ob is not None:
            context["side_relative_to_ob"] = side_relative_to_ob

        return context

    # ------------------------------------------------------------------
    # Fibonacci context builder (exact percentage + level + zone)
    # ------------------------------------------------------------------

    def build_fib_context(
        self,
        price: float,
        retracement: Optional[FibonacciRetracement],
    ) -> Optional[dict]:
        """Build precise Fibonacci context for a candidate entry price.

        Returns a structured dict containing:

        - ``percentage``: the exact retracement percentage in [0, 1]
          that the entry price falls on, measured along the swing leg
          (swing_low → swing_high for bullish, swing_high → swing_low
          for bearish).  Rounded to 4 decimals.
        - ``percentage_str``: the same value formatted to 3 decimals as
          a string, suitable for SMCCandidate.fib_level which is typed
          Optional[str].
        - ``zone``: the PriceZone (PREMIUM / EQUILIBRIUM / DISCOUNT)
          the entry sits in, per SMC-MIT-003.
        - ``is_in_ote``: True if the entry is within the configured
          pip tolerance of the 61.8%–78.6% OTE pocket.
        - ``nearest_level_name``: the closest named Fibonacci level
          (e.g. ``"0.618"``) to the entry.
        - ``nearest_level_price``: the exact price of that nearest
          level on this retracement.
        - ``swing_high`` / ``swing_low``: the retracement bounds.
        - ``swing_high_timestamp`` / ``swing_low_timestamp``: ISO-8601
          timestamps of those swings.
        - ``retracement_direction``: ``"BULLISH"`` if the leg is
          low→high (buys), ``"BEARISH"`` if high→low (sells).

        Returns ``None`` if ``retracement`` is ``None`` or the range is
        degenerate (swing_high == swing_low, which the model prevents
        but we guard defensively).
        """
        if retracement is None:
            return None

        range_size = retracement.swing_high - retracement.swing_low
        if range_size <= 0:
            return None

        # A retracement percentage is only physically meaningful when the
        # entry price lies within the swing leg.  Outside of it, the
        # candidate is on a different structural leg and the fib context
        # would be misleading (negative values or values > 1.0).  Return
        # None so the candidate omits fib_context entirely rather than
        # feeding the LLM nonsense.
        if price < retracement.swing_low or price > retracement.swing_high:
            return None

        if retracement.is_bullish:
            # Buys: 0% at the swing low, 100% at the swing high.
            # A retracement at the OB entry measures how far price has
            # pulled back from the swing high toward the swing low.
            percentage = (retracement.swing_high - price) / range_size
        else:
            # Sells: 0% at the swing high, 100% at the swing low.
            percentage = (price - retracement.swing_low) / range_size

        zone = self.fibonacci_analyzer.get_zone_for_price(price, retracement)
        is_in_ote = self.fibonacci_analyzer.is_at_ote(
            price,
            retracement,
            tolerance_pips=self.config.fibonacci_tolerance_pips,
        )

        # Find the nearest named Fibonacci level by value distance.
        nearest_level = min(
            FIBONACCI_VALUES.items(),
            key=lambda kv: abs(percentage - kv[1]),
        )
        nearest_level_enum: FibonacciLevel = nearest_level[0]
        nearest_level_value: float = nearest_level[1]
        nearest_level_price = retracement.get_level_price(nearest_level_enum)

        percentage_rounded = round(percentage, 4)
        percentage_str = f"{percentage_rounded:.3f}"

        return {
            "percentage": percentage_rounded,
            "percentage_str": percentage_str,
            "zone": zone.value,
            "is_in_ote": is_in_ote,
            "nearest_level_name": str(nearest_level_value),
            "nearest_level_price": round(nearest_level_price, 5),
            "swing_high": retracement.swing_high,
            "swing_low": retracement.swing_low,
            "swing_high_timestamp": retracement.swing_high_timestamp.isoformat(),
            "swing_low_timestamp": retracement.swing_low_timestamp.isoformat(),
            "retracement_direction": (
                Direction.BULLISH.value
                if retracement.is_bullish
                else Direction.BEARISH.value
            ),
        }

    # ------------------------------------------------------------------
    # Zone freshness (mitigation detection)
    # ------------------------------------------------------------------

    def validate_zone_freshness(
        self,
        ob: OrderBlock,
        sequence: CandleSequence,
    ) -> bool:
        """Validate zone is unmitigated (fresh) based on structural breaks.

        An Order Block remains structurally valid (fresh for an entry) until price
        completely breaks it. A deep tap (50-90%) into the OB is normal mitigation
        behavior before price continues in the original direction, and is precisely
        what triggers our entry.
        
        The OB is only invalidated (destroyed, potentially becoming a Breaker Block)
        if a candle CLOSES completely beyond its extreme boundary. Any past candle
        that only severely wicked into it is considered the RTO leg itself.
        """
        if ob.candle_index >= len(sequence.candles) - 1:
            return True

        for i in range(ob.candle_index + 1, len(sequence.candles)):
            candle = sequence.candles[i]

            if ob.direction == Direction.BULLISH:
                # Bullish OB (demand zone): Invalidated if price CLOSES completely below the low.
                if candle.close < ob.lower_bound:
                    return False

            else:
                # Bearish OB (supply zone): Invalidated if price CLOSES completely above the high.
                if candle.close > ob.upper_bound:
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
