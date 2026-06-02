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

from engine.shared.risk import (
    LOWEST_STYLE_MIN_RR as _LOWEST_STYLE_MIN_RR,
    STYLE_MIN_TP_RR,
    style_min_tp_rr,
)
from engine.ta.common.utils.price.math import get_pip_value
from engine.ta.constants import Direction, Timeframe, TIMEFRAME_MINUTES

# Re-exported for existing TA callers that import these names from this
# module.  The canonical definitions live in engine.shared.risk.
__all__ = [
    "STYLE_MIN_TP_RR",
    "style_min_tp_rr",
    "TIMEFRAME_SL_FLOOR_PIPS",
    "TIMEFRAME_MIN_TP_RR",
    "timeframe_floor_pips",
    "timeframe_min_tp_rr",
    "resolve_min_tp_rr",
    "structural_buffer",
    "compute_structural_stop_loss",
]

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


# --- Timeframe-scaled minimum take-profit R:R ------------------------
#
# IMPORTANT: these values are reward-to-risk MULTIPLES (R), NOT pips.
# A value of 3.0 means the take-profit must be at least 3x the SL
# distance away from entry (a 1:3 R:R floor).  The actual TP is always
# a real structural liquidity level; this only filters out targets too
# close to clear the floor.
#
# An LTF target and an HTF target cannot share the same R:R floor: an
# M5 entry draws to the nearest LTF liquidity pool, while a D1 entry
# must reach a far HTF draw.  This table scales the floor up with the
# timeframe.
#
# CRITICAL CONSISTENCY RULE: this floor must NEVER sit below the
# rulebook's lowest per-style minimum R:R (Scalping = 1:2, Section 7.3
# / STYLE-RR-001), imported as _LOWEST_STYLE_MIN_RR from
# engine.shared.risk.  The authoritative per-style gate is the
# processor validator (_validate_rr_ratio); see resolve_min_tp_rr()
# for how the style and timeframe floors combine.
TIMEFRAME_MIN_TP_RR: dict[Timeframe, float] = {
    Timeframe.M1: 2.0,
    Timeframe.M5: 2.0,
    Timeframe.M15: 2.5,
    Timeframe.M30: 2.5,
    Timeframe.H1: 3.0,
    Timeframe.H3: 3.0,
    Timeframe.H4: 3.5,
    Timeframe.H6: 3.5,
    Timeframe.H8: 4.0,
    Timeframe.H12: 4.0,
    Timeframe.D1: 5.0,
    Timeframe.W1: 5.0,
    Timeframe.MN1: 5.0,
}


def timeframe_min_tp_rr(timeframe: Timeframe) -> float:
    """Return the timeframe-scaled minimum take-profit reward-to-risk MULTIPLE.

    This is an R multiple (e.g. 3.0 == 1:3 R:R), never a pip distance.
    It is floored at the lowest rulebook per-style minimum so it can
    never undershoot the style gate enforced downstream.
    """
    return max(
        _LOWEST_STYLE_MIN_RR,
        TIMEFRAME_MIN_TP_RR.get(timeframe, _LOWEST_STYLE_MIN_RR),
    )


def resolve_min_tp_rr(
    timeframe: Optional[Timeframe] = None,
    style_min_rr: Optional[float] = None,
    *,
    style: Optional[str] = None,
) -> float:
    """Combine the per-style minimum R:R with the timeframe floor.

    The take-profit floor is ``max(style_floor, timeframe_floor)``:

    * The style floor is the rulebook's per-style minimum (Section 7.3
      / STYLE-RR-001): Scalping 2.0, Intraday 3.0, Swing 3.0,
      Positional 5.0.  It may be supplied either as a number
      (``style_min_rr``) or by name (``style``); the name form looks it
      up in ``STYLE_MIN_TP_RR``.  It is the HARD floor -- the timeframe
      value may only RAISE the bar above it, never lower it.
    * The timeframe floor widens the bar when the candidate's own
      timeframe demands a larger draw than the active style requires
      (e.g. a D1 candidate inside a Swing trade).

    Either input may be omitted:
    * No timeframe (processor validator, which knows style but not the
      candidate timeframe) -> the style floor alone applies.
    * No style (candidate-build TA layer, which knows timeframe but not
      the active style) -> the timeframe floor alone applies, and that
      floor is itself never below the lowest style minimum.
    """
    resolved_style_rr = style_min_rr
    if resolved_style_rr is None and style is not None:
        resolved_style_rr = style_min_tp_rr(style)

    tf_floor = (
        timeframe_min_tp_rr(timeframe) if timeframe is not None else None
    )

    candidates = [
        v for v in (resolved_style_rr, tf_floor) if v is not None
    ]
    if not candidates:
        return _LOWEST_STYLE_MIN_RR
    return max(float(v) for v in candidates)


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
