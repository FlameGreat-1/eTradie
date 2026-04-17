"""Per-candidate Fibonacci retracement leg selection.

This module centralizes the rule that the Fibonacci retracement used
to score an SMC candidate must be drawn on *that candidate's own*
structural impulse leg — not on a globally-selected HTF leg.

Authoritative references:
  - knowledge/frameworks/smc_framework.md :: SMC-MIT-003
    (Premium/Discount drawn swing-high -> swing-low for sells,
     swing-low -> swing-high for buys)
  - docs/ta/SMC.txt :: Universal Rule 6
    ("OTE alone means nothing — it only counts when it lands on an
     already valid OB.")
  - docs/ta/SMC.txt :: The 7 Rules of a Tradeable Order Block (Rule 5)

Design policy (enforced here, no exceptions):

  1. Direction-correct leg per pattern.
     A bullish candidate is measured on an up-leg (low -> high with
     is_bullish=True).  A bearish candidate is measured on a down-leg
     (high -> low with is_bullish=False).  The two must never be
     crossed; doing so was the historical bug fixed by this module.

  2. Setup-specific endpoints.
     The leg's endpoints come from the candidate's own structural
     events (sweep.swept_level, bms.breakout_price, sms.failed_level,
     choch.broken_level / breakout_price, amd_context.asian_range),
     never from a global HTF swing scan.

  3. No fallback.
     When any required endpoint is missing or the resulting leg is
     degenerate (high <= low), the selector returns None.  The
     candidate is still emitted by its builder, but with
     fib_level=None and no fib_context in metadata.  We do not
     fabricate a leg.  This function is a pure reporter of
     structural truth.

The public API is a small set of select_leg_* functions, one per
candidate pattern family.  Each returns Optional[FibonacciRetracement].
Builders are expected to call the matching selector and pass the
result verbatim to the existing zone-validator / fib-context machinery.

This module deliberately has no dependency on the builders or the
SMCDetector, and no side effects.  It can be exercised in isolation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from engine.shared.exceptions import ConfigurationError
from engine.shared.logging import get_logger
from engine.ta.constants import Timeframe
from engine.ta.models.fibonacci import FibonacciRetracement
from engine.ta.models.liquidity_event import LiquiditySweep
from engine.ta.models.structure_event import (
    BreakInMarketStructure,
    ChangeOfCharacter,
    ShiftInMarketStructure,
)
from engine.ta.models.swing import SwingHigh, SwingLow

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Low-level construction helper
# ---------------------------------------------------------------------------


def _build(
    *,
    symbol: str,
    timeframe: Timeframe,
    swing_high: Optional[float],
    swing_low: Optional[float],
    swing_high_timestamp: Optional[datetime],
    swing_low_timestamp: Optional[datetime],
    is_bullish: bool,
) -> Optional[FibonacciRetracement]:
    """Construct a FibonacciRetracement from resolved endpoints.

    Returns None (never raises) when any endpoint is missing or the
    resulting leg is degenerate.  Degeneracy is defined strictly:
    ``swing_high <= swing_low`` — the FibonacciRetracement model
    itself rejects that invariant, but we prefer a None return over
    a ConfigurationError because a missing leg is an expected outcome
    on data-thin analyses, not an exceptional condition.
    """
    if swing_high is None or swing_low is None:
        return None
    if swing_high_timestamp is None or swing_low_timestamp is None:
        return None
    if swing_high <= swing_low:
        return None

    try:
        return FibonacciRetracement(
            symbol=symbol,
            timeframe=timeframe,
            swing_high=swing_high,
            swing_low=swing_low,
            swing_high_timestamp=swing_high_timestamp,
            swing_low_timestamp=swing_low_timestamp,
            is_bullish=is_bullish,
        )
    except ConfigurationError:
        # Defensive: should be unreachable given the guards above, but
        # we never want leg selection to kill a candidate by raising.
        return None


# ---------------------------------------------------------------------------
# Pattern-specific selectors
#
# Each selector takes only what the corresponding candidate already
# carries as structural evidence.  No global state, no HTF re-scans.
# ---------------------------------------------------------------------------


def select_leg_for_sh_bms_rto(
    *,
    symbol: str,
    timeframe: Timeframe,
    htf_bms: BreakInMarketStructure,
    sweep: Optional[LiquiditySweep],
    is_bullish: bool,
) -> Optional[FibonacciRetracement]:
    """Leg for SH + BMS + RTO (Patterns 2 / 7).

    The impulse starts at the liquidity sweep (SSL for bullish,
    BSL for bearish) and terminates at the BMS breakout close, by
    definition of the pattern per docs/ta/SMC.txt Pattern 2 / 7.

    A continuation candidate without an associated sweep therefore
    has no direction-correct leg and returns None.  This is the
    correct behaviour: Universal Rule 1 ("Liquidity Must Be Taken
    First") makes the sweep a precondition of the setup's OTE
    reading; scoring fib without it would be measuring against an
    arbitrary leg.
    """
    if sweep is None:
        return None

    if is_bullish:
        return _build(
            symbol=symbol,
            timeframe=timeframe,
            swing_low=sweep.swept_level,
            swing_low_timestamp=sweep.timestamp,
            swing_high=htf_bms.breakout_price,
            swing_high_timestamp=htf_bms.timestamp,
            is_bullish=True,
        )

    return _build(
        symbol=symbol,
        timeframe=timeframe,
        swing_high=sweep.swept_level,
        swing_high_timestamp=sweep.timestamp,
        swing_low=htf_bms.breakout_price,
        swing_low_timestamp=htf_bms.timestamp,
        is_bullish=False,
    )


def select_leg_for_sms_bms_rto(
    *,
    symbol: str,
    timeframe: Timeframe,
    htf_sms: ShiftInMarketStructure,
    ltf_bms: BreakInMarketStructure,
    is_bullish: bool,
) -> Optional[FibonacciRetracement]:
    """Leg for SMS + BMS + RTO (Patterns 3 / 8).

    The impulse is anchored by the SMS failure level (the swing that
    held) at one end and the confirming opposite-direction BMS
    breakout close at the other.
    """
    if is_bullish:
        return _build(
            symbol=symbol,
            timeframe=timeframe,
            swing_low=htf_sms.failed_level,
            swing_low_timestamp=htf_sms.failed_level_timestamp,
            swing_high=ltf_bms.breakout_price,
            swing_high_timestamp=ltf_bms.timestamp,
            is_bullish=True,
        )

    return _build(
        symbol=symbol,
        timeframe=timeframe,
        swing_high=htf_sms.failed_level,
        swing_high_timestamp=htf_sms.failed_level_timestamp,
        swing_low=ltf_bms.breakout_price,
        swing_low_timestamp=ltf_bms.timestamp,
        is_bullish=False,
    )


def select_leg_for_choch_bms_rto(
    *,
    symbol: str,
    timeframe: Timeframe,
    htf_choch: ChangeOfCharacter,
    is_bullish: bool,
) -> Optional[FibonacciRetracement]:
    """Leg for CHOCH + BMS + RTO.

    CHoCH is the earliest reversal signal per SMC-CHOCH-001/002.  Its
    broken_level is the last opposing swing (LH for a bullish CHoCH,
    HL for a bearish CHoCH) and its breakout_price is the close that
    took it out.  Those two anchor the reversal impulse leg directly.
    """
    if is_bullish:
        return _build(
            symbol=symbol,
            timeframe=timeframe,
            swing_low=htf_choch.broken_level,
            swing_low_timestamp=htf_choch.broken_level_timestamp,
            swing_high=htf_choch.breakout_price,
            swing_high_timestamp=htf_choch.timestamp,
            is_bullish=True,
        )

    return _build(
        symbol=symbol,
        timeframe=timeframe,
        swing_high=htf_choch.broken_level,
        swing_high_timestamp=htf_choch.broken_level_timestamp,
        swing_low=htf_choch.breakout_price,
        swing_low_timestamp=htf_choch.timestamp,
        is_bullish=False,
    )


def select_leg_for_amd(
    *,
    symbol: str,
    timeframe: Timeframe,
    asian_range_high: Optional[float],
    asian_range_low: Optional[float],
    asian_range_start: Optional[datetime],
    asian_range_end: Optional[datetime],
    ltf_bms: BreakInMarketStructure,
    is_bullish: bool,
) -> Optional[FibonacciRetracement]:
    """Leg for the AMD Distribution phase (Patterns 4 / 9).

    During the manipulation phase price sweeps the Asian range on the
    wrong side; during distribution it reverses to the true direction
    and confirms via BMS.  The impulse leg therefore runs:

      - Bullish AMD: from the Asian range low (manipulation extreme)
        up to the BMS breakout close.
      - Bearish AMD: from the Asian range high down to the BMS
        breakout close.

    The caller is expected to derive asian_range_{high,low,start,end}
    from amd_context.asian_range; this selector takes primitives so
    it does not need to import AMDContext.
    """
    # Prefer the most specific timestamps available, but degrade
    # gracefully to the BMS timestamp for the range end if the caller
    # only has the range start (some DealingRange instances have
    # end_time=None during the live/unclosed session).
    if asian_range_end is None:
        asian_range_end = ltf_bms.timestamp
    if asian_range_start is None:
        asian_range_start = asian_range_end

    if is_bullish:
        return _build(
            symbol=symbol,
            timeframe=timeframe,
            swing_low=asian_range_low,
            swing_low_timestamp=asian_range_start,
            swing_high=ltf_bms.breakout_price,
            swing_high_timestamp=ltf_bms.timestamp,
            is_bullish=True,
        )

    return _build(
        symbol=symbol,
        timeframe=timeframe,
        swing_high=asian_range_high,
        swing_high_timestamp=asian_range_start,
        swing_low=ltf_bms.breakout_price,
        swing_low_timestamp=ltf_bms.timestamp,
        is_bullish=False,
    )


def select_leg_for_turtle_soup_long(
    *,
    symbol: str,
    timeframe: Timeframe,
    sweep: LiquiditySweep,
    swing_highs: list[SwingHigh],
) -> Optional[FibonacciRetracement]:
    """Leg for TURTLE_SOUP_LONG (Pattern 6).

    The sweep takes an SSL below a prior structural low; the relevant
    impulse for an OTE reading runs from that swept low back up to
    the nearest structural swing high that is actually above the
    swept level.  If no such swing high exists in the supplied list,
    there is no direction-correct leg and we return None.
    """
    if sweep is None:
        return None

    eligible = [sh for sh in (swing_highs or []) if sh.price > sweep.swept_level]
    if not eligible:
        return None

    # Pick the closest swing high above the swept level — that is the
    # immediate impulse target price ran toward after the sweep.
    anchor = min(eligible, key=lambda sh: sh.price - sweep.swept_level)

    return _build(
        symbol=symbol,
        timeframe=timeframe,
        swing_low=sweep.swept_level,
        swing_low_timestamp=sweep.timestamp,
        swing_high=anchor.price,
        swing_high_timestamp=anchor.timestamp,
        is_bullish=True,
    )


def select_leg_for_turtle_soup_short(
    *,
    symbol: str,
    timeframe: Timeframe,
    sweep: LiquiditySweep,
    swing_lows: list[SwingLow],
) -> Optional[FibonacciRetracement]:
    """Leg for TURTLE_SOUP_SHORT (Pattern 1).

    Symmetric to ``select_leg_for_turtle_soup_long``.  Anchors the
    leg between the BSL that was swept and the nearest swing low
    below it.
    """
    if sweep is None:
        return None

    eligible = [sl for sl in (swing_lows or []) if sl.price < sweep.swept_level]
    if not eligible:
        return None

    anchor = min(eligible, key=lambda sl: sweep.swept_level - sl.price)

    return _build(
        symbol=symbol,
        timeframe=timeframe,
        swing_high=sweep.swept_level,
        swing_high_timestamp=sweep.timestamp,
        swing_low=anchor.price,
        swing_low_timestamp=anchor.timestamp,
        is_bullish=False,
    )
