"""Centralised entry / stop-loss / take-profit geometry for SnD builders.

All SnD candidate builders (QM, fakeout king, continuation, in both
directions) need to translate a structural anchor + a configured
SL-buffer (in pips) into a concrete `(entry_price, stop_loss,
take_profit)` triple at a fixed risk-reward.

Prior to this module, the same eight-line block was copy-pasted into
eight different builders.  All eight shared the same latent crash:
when the structural extreme sat far from the entry (e.g. QML/QMH on
Deriv synthetic indices), `risk * RR` could exceed the entry price and
drive the take-profit below zero, which then failed pydantic's
`take_profit > 0` validator and propagated up as
`ta_mtf_analysis_failed`, killing the analysis for that symbol.

This module replaces those eight blocks with one pure helper that:

* Uses the broker-aware pip utilities from
  ``engine.ta.common.utils.price.math`` so the SL buffer is computed
  correctly for FX, JPY pairs, metals, oil, indices, crypto and the
  Deriv synthetic families (JUMP, CRASH/BOOM, VOLATILITY, STEP, etc.).
* Enforces full geometric invariants (positivity + direction-correct
  ordering of entry/SL/TP).
* Returns ``None`` with a single debug log line when the structural
  geometry is impossible for the instrument, instead of letting a
  pydantic ``ValidationError`` abort the orchestrator.

No hardcoded prices, pip values, or instrument heuristics live here -
the instrument classification lives in
``engine.ta.common.utils.price.math`` and is the single source of
truth.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.shared.logging import get_logger
from engine.ta.common.utils.price.math import (
    calculate_price_from_pips,
    get_pip_value,
)
from engine.ta.common.utils.price.stop_loss import (
    resolve_min_tp_rr,
    timeframe_floor_pips,
)
from engine.ta.constants import Direction, Timeframe

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TradeLevels:
    """Resolved entry / stop-loss / take-profit for a candidate.

    All three values are guaranteed by :func:`compute_trade_levels` to
    be strictly positive and ordered consistently with ``direction``:

    * ``BEARISH`` -> ``take_profit < entry_price < stop_loss``
    * ``BULLISH`` -> ``stop_loss < entry_price < take_profit``

    ``risk`` is the absolute price distance between ``entry_price`` and
    ``stop_loss`` (always > 0).
    """

    entry_price: float
    stop_loss: float
    take_profit: float
    risk: float


def compute_trade_levels(
    *,
    symbol: str,
    direction: Direction,
    entry_price: float,
    structural_extreme: float | None,
    sl_buffer_pips: float,
    risk_reward: float | None = None,
    timeframe: Timeframe | None = None,
    logger_event_prefix: str = "snd_builder",
) -> TradeLevels | None:
    """Compute entry / SL / TP from structure + a pip-denominated SL buffer.

    The SL is placed beyond the structural extreme (the QM ``hh_price``
    for shorts, ``ll_price`` for longs, or the flip / zone level when no
    structural extreme is available) by ``sl_buffer_pips`` pips.  The TP
    is placed at ``risk * risk_reward`` from the entry in the trade
    direction.

    All pip-to-price conversion uses
    :func:`engine.ta.common.utils.price.math.calculate_price_from_pips`,
    which delegates to :func:`get_pip_value` for instrument-aware pip
    sizing.  No hardcoded pip values are introduced here.

    Parameters
    ----------
    symbol:
        Broker symbol.  Used by ``get_pip_value`` to classify the
        instrument (FX / JPY / metal / oil / index / crypto / Deriv
        synthetic) and pick the correct pip size.
    direction:
        ``Direction.BEARISH`` (short) or ``Direction.BULLISH`` (long).
        ``Direction.NEUTRAL`` is rejected.
    entry_price:
        Planned entry price.  Must be > 0.
    structural_extreme:
        Price of the structural anchor used to seat the SL.  For QM
        shorts this is ``qml.hh_price``; for QMH longs this is
        ``qmh.ll_price``; for flip-based builders (fakeout king,
        continuation) this is typically ``None`` and the SL is seated
        off the entry / flip level itself.
    sl_buffer_pips:
        Distance in pips beyond the SL anchor.  Sourced from
        ``SnDConfig.previous_level_tolerance_pips``.
    risk_reward:
        TP multiple of risk.  Defaults to ``3.0`` to match the existing
        builder behaviour.
    logger_event_prefix:
        Tag used when a geometry-rejection debug event is emitted, so
        the caller is identifiable in logs.

    Returns
    -------
    TradeLevels | None
        ``None`` when the inputs are non-finite / non-positive, when
        ``direction`` is not BULLISH/BEARISH, or when the resulting
        triple cannot satisfy the positivity + ordering invariants for
        this symbol (geometrically impossible setup - logged at DEBUG).
    """
    # Reject obviously invalid scalar inputs up front - this catches NaN,
    # +/- inf and non-positive prices without any further computation.
    if not _is_positive_finite(entry_price):
        return None
    if not _is_non_negative_finite(sl_buffer_pips):
        return None

    # TP reward-to-risk MULTIPLE.  Resolve from the timeframe floor
    # (never below the rulebook's lowest style minimum) unless an
    # explicit risk_reward was supplied by the caller.  Falls back to
    # 3.0 (legacy SnD default) only when neither is available.
    if risk_reward is None:
        risk_reward = resolve_min_tp_rr(timeframe) if timeframe is not None else 3.0
    if not _is_positive_finite(risk_reward):
        return None
    if structural_extreme is not None and not _is_positive_finite(structural_extreme):
        return None

    if direction not in (Direction.BEARISH, Direction.BULLISH):
        logger.debug(
            f"{logger_event_prefix}_invalid_direction",
            extra={"symbol": symbol, "direction": str(direction)},
        )
        return None

    # Timeframe-aware structural buffer.  The configured pip offset is
    # a floor; when a timeframe is supplied we widen it to the
    # timeframe-scaled minimum so HTF and synthetic stops are not as
    # tight as a flat 3-pip offset.  get_pip_value() encodes the
    # per-instrument pip size (FX 0.0001, JPY/metals 0.01,
    # indices/crypto/synthetics 1.0).
    effective_buffer_pips = float(sl_buffer_pips)
    if timeframe is not None:
        effective_buffer_pips = max(effective_buffer_pips, timeframe_floor_pips(timeframe))
    sl_buffer_pips = effective_buffer_pips
    sl_buffer_price = float(get_pip_value(symbol)) * float(sl_buffer_pips)

    if direction == Direction.BEARISH:
        # SL sits ABOVE the structural extreme (or entry if absent).
        sl_anchor = structural_extreme if structural_extreme is not None else entry_price
        stop_loss = calculate_price_from_pips(
            base_price=sl_anchor,
            pips=sl_buffer_pips,
            symbol=symbol,
            direction=1,
        )
        # Defensive: if the anchor was below entry (shouldn't happen for
        # a well-formed QML, but possible for malformed inputs), force
        # the SL strictly above entry by re-seating off entry.
        if stop_loss <= entry_price:
            stop_loss = entry_price + sl_buffer_price

        risk = stop_loss - entry_price
        take_profit = entry_price - (risk * risk_reward)
    else:  # BULLISH
        # SL sits BELOW the structural extreme (or entry if absent).
        sl_anchor = structural_extreme if structural_extreme is not None else entry_price
        stop_loss = calculate_price_from_pips(
            base_price=sl_anchor,
            pips=sl_buffer_pips,
            symbol=symbol,
            direction=-1,
        )
        if stop_loss >= entry_price:
            stop_loss = entry_price - sl_buffer_price

        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * risk_reward)

    if not _validate_geometry(
        symbol=symbol,
        direction=direction,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk=risk,
        logger_event_prefix=logger_event_prefix,
    ):
        return None

    return TradeLevels(
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk=risk,
    )


def _validate_geometry(
    *,
    symbol: str,
    direction: Direction,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    risk: float,
    logger_event_prefix: str,
) -> bool:
    """Enforce positivity + direction-correct ordering of the triple.

    Logs a single DEBUG event when the triple is invalid so the
    skipped-candidate cause is visible without escalating to ERROR
    (geometric rejection is an expected outcome for some instruments,
    not a fault).
    """
    if not (
        _is_positive_finite(entry_price)
        and _is_positive_finite(stop_loss)
        and _is_positive_finite(take_profit)
        and _is_positive_finite(risk)
    ):
        logger.debug(
            f"{logger_event_prefix}_skipped_non_positive_levels",
            extra={
                "symbol": symbol,
                "direction": str(direction),
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk": risk,
            },
        )
        return False

    if direction == Direction.BEARISH:
        if not (take_profit < entry_price < stop_loss):
            logger.debug(
                f"{logger_event_prefix}_skipped_invalid_short_geometry",
                extra={
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                },
            )
            return False
    elif not (stop_loss < entry_price < take_profit):
        logger.debug(
            f"{logger_event_prefix}_skipped_invalid_long_geometry",
            extra={
                "symbol": symbol,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            },
        )
        return False

    return True


def _is_positive_finite(value: float) -> bool:
    """True iff value is a finite float strictly greater than zero."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    if v != v:  # NaN
        return False
    if v in (float("inf"), float("-inf")):
        return False
    return v > 0.0


def _is_non_negative_finite(value: float) -> bool:
    """True iff value is a finite float >= 0."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    if v != v:  # NaN
        return False
    if v in (float("inf"), float("-inf")):
        return False
    return v >= 0.0
