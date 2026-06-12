"""Canonical risk constants shared across engine layers.

Single source of truth for the per-trading-style minimum
reward-to-risk multiples defined by the rulebook (Section 7.3 /
STYLE-RR-001).  Both the TA candidate layer
(``engine.ta.common.utils.price.stop_loss``) and the processor
validator (``engine.processor.parsing.validators``) import these from
here so the style floor can never drift between layers.

Values are reward-to-risk MULTIPLES (R), never pip distances:
    Scalping   1:2  -> 2.0
    Intraday   1:3  -> 3.0
    Swing      1:3  -> 3.0
    Positional 1:5  -> 5.0
"""

from __future__ import annotations

from typing import Final

MIN_RR_SCALPING: Final[float] = 2.0
MIN_RR_INTRADAY: Final[float] = 3.0
MIN_RR_SWING: Final[float] = 3.0
MIN_RR_POSITIONAL: Final[float] = 5.0

# Lowest per-style minimum -- used as the safe lower bound by any
# layer that does not yet know the active trading style.
LOWEST_STYLE_MIN_RR: Final[float] = MIN_RR_SCALPING

STYLE_MIN_TP_RR: Final[dict[str, float]] = {
    "SCALPING": MIN_RR_SCALPING,
    "INTRADAY": MIN_RR_INTRADAY,
    "SWING": MIN_RR_SWING,
    "POSITIONAL": MIN_RR_POSITIONAL,
}


def style_min_tp_rr(style: str | None) -> float | None:
    """Return the rulebook per-style minimum R:R, or None if unknown."""
    if style is None:
        return None
    return STYLE_MIN_TP_RR.get(style.strip().upper())
