"""Structural, timeframe-aware stop-loss geometry.

Single source of truth for translating a setup's *real* structural
invalidation level into a concrete stop-loss price for every framework
(SMC continuation / reversal / CHoCH / AMD, and SnD QM / fakeout /
continuation).

Design principles (all enforced here, none indicator-based):

1. REAL INVALIDATION ANCHOR
   The SL is seated on the price level that genuinely invalidates the
   setup -- the CHoCH ``broken_level``, the SMS ``failed_level``, the
   liquidity-sweep extreme, or the Quasimodo head (``hh_price`` /
   ``ll_price``).  It is NEVER confined to the Order Block edge.  The
   OB edge is only used as an *inner* guard (the SL may not end up on
   the wrong side of the OB), never as the anchor.

2. STRUCTURAL BUFFER, NOT A FLAT PIP OFFSET
   The buffer placed beyond the invalidation level is the larger of:
     - a fraction of the invalidation candle's own range (when the
       caller can supply that range), and
     - a timeframe-scaled floor expressed in pips.
   A flat 3-5 pip offset is too tight, especially on synthetics where
   one pip == one index point; the timeframe floor fixes that.

3. TIMEFRAME MATTERS
   An M15 stop and a D1 stop cannot share the same buffer.  The floor
   scales monotonically with ``TIMEFRAME_MINUTES`` so higher
   timeframes get materially wider structural breathing room.

The helper is pure: no I/O, no logging side effects, deterministic for
a given input.
"""

from __future__ import annotations

from typing import Optional

from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import Direction, Timeframe, TIMEFRAME_MINUTES

# --- Timeframe-scaled minimum SL buffer (in pips) ---------------------
#
# These are the *floor* distances placed beyond the structural
# invalidation level, expressed in the instrument's pip unit
# (get_pip_value()).  They are deliberately well above the old flat
# 3-5 pip offset so a single retest wick cannot clip the stop, and
# they grow with the timeframe because an HTF invalidation needs a
# proportionally wider tolerance than an LTF one.
#
# For synthetics / indices / crypto pip_value == 1.0, so the value is
# read directly as points.  For FX (pip_value 0.0001) and JPY/metals
# (0.01) the same pip count converts to the correct price distance via
# get_pip_value(), so one table works across every instrument class.
TIMEFRAME_SL_FLOOR_PIPS: dict[Timeframe, float] = {
    Timeframe.M1: 8.0,
    Timeframe.M5: 12.0,
    Timeframe.M15: 18.0,
    Timeframe.M30: 25.0,
    Timeframe.H1: 35.0,
    Timeframe.H3: 55.0,
    Timeframe.H4: 70.0,
    Timeframe.H6: 90.0,
    Timeframe.H8: 110.0,
    Timeframe.H12: 140.0,
    Timeframe.D1: 200.0,
    Timeframe.W1: 400.0,
    Timeframe.MN1: 700.0,
}

# Default floor used when a timeframe is somehow absent from the table
# (should never happen -- every Timeframe enum member is listed above).
_DEFAULT_FLOOR_PIPS: float = 35.0

# Fraction of the invalidation candle's own range added beyond the
# invalidation level when that range is available.  Structural, not an
# indicator: the candle that set the invalidation level defines how
# much noise lives around it.
_INVALIDATION_RANGE_BUFFER_PCT: float = 0.25


def timeframe_floor_pips(timeframe: Timeframe) -> float:
    """Return the timeframe-scaled minimum SL buffer in pips."""
    return TIMEFRAME_SL_FLOOR_PIPS.get(timeframe, _DEFAULT_FLOOR_PIPS)


def structural_buffer(
    *,
    symbol: str,
    timeframe: Timeframe,
    invalidation_candle_range: Optional[float] = None,
) -> float:
    """Compute the price-distance buffer to place beyond the invalidation level.

    buffer = max(invalidation_candle_range * range_pct,
                 timeframe_floor_pips * pip_value)

    ``invalidation_candle_range`` is the high-low range of the candle
    that produced the invalidation level (the sweep candle, the CHoCH/
    SMS break candle, or the QM head candle).  When the caller cannot
    supply it, only the timeframe floor applies.
    """
    pip_value = float(get_pip_value(symbol))
    floor = timeframe_floor_pips(timeframe) * pip_value

    if invalidation_candle_range is not None and invalidation_candle_range > 0:
        range_component = invalidation_candle_range * _INVALIDATION_RANGE_BUFFER_PCT
        return max(range_component, floor)

    return floor


def compute_structural_stop_loss(
    *,
    symbol: str,
    timeframe: Timeframe,
    direction: Direction,
    invalidation_level: float,
    ob_inner_edge: Optional[float] = None,
    invalidation_candle_range: Optional[float] = None,
) -> float:
    """Compute a stop-loss seated beyond the real structural invalidation.

    Parameters
    ----------
    direction:
        ``BEARISH`` (short) -> SL sits ABOVE the invalidation level.
        ``BULLISH`` (long)  -> SL sits BELOW the invalidation level.
    invalidation_level:
        The price that genuinely invalidates the setup -- CHoCH
        ``broken_level``, SMS ``failed_level``, the swept liquidity
        extreme, or the QM head.  This is the anchor; the SL is placed
        one ``structural_buffer`` beyond it.
    ob_inner_edge:
        The far edge of the Order Block (``upper_bound`` for shorts,
        ``lower_bound`` for longs).  Used ONLY as an inner guard: the
        SL must still sit beyond this edge so it is never inside the
        zone.  It is never used as the anchor.  Pass ``None`` for
        setups without an OB (turtle soup, SnD flips).
    invalidation_candle_range:
        High-low range of the candle that produced ``invalidation_
        level``; widens the buffer structurally when available.
    """
    buffer = structural_buffer(
        symbol=symbol,
        timeframe=timeframe,
        invalidation_candle_range=invalidation_candle_range,
    )

    if direction == Direction.BEARISH:
        sl = invalidation_level + buffer
        # Inner guard: never tighter than the OB upper edge + buffer.
        if ob_inner_edge is not None:
            sl = max(sl, ob_inner_edge + buffer)
        return sl

    sl = invalidation_level - buffer
    if ob_inner_edge is not None:
        sl = min(sl, ob_inner_edge - buffer)
    return sl
