"""Extract RAG-relevant signals from TA output.

Pure functions - no I/O, no side effects.
"""

from __future__ import annotations

from typing import Optional

from engine.shared.models.base import FrozenModel
from gateway.context.models import TASymbolResult


class TASignals(FrozenModel):
    """Extracted TA signals for a single symbol."""

    symbol: str
    framework: Optional[str] = None
    setup_family: Optional[str] = None
    direction: Optional[str] = None
    htf_timeframe: Optional[str] = None
    ltf_timeframe: Optional[str] = None
    session_context: Optional[str] = None
    patterns_detected: list[str] = []
    has_bms: bool = False
    has_choch: bool = False
    has_sms: bool = False
    has_liquidity_sweep: bool = False
    has_order_block: bool = False
    has_fvg: bool = False
    has_qml: bool = False
    has_sr_flip: bool = False
    has_fakeout: bool = False
    has_marubozu: bool = False
    has_compression: bool = False
    trend_direction: Optional[str] = None


def extract_ta_signals(result: TASymbolResult) -> TASignals:
    """Extract RAG-relevant signals from a single symbol's TA result."""
    if result.status != "success":
        return TASignals(symbol=result.symbol)

    smc_candidates = result.smc_candidates
    snd_candidates = result.snd_candidates
    snapshot = result.snapshot or {}

    framework = _determine_framework(smc_candidates, snd_candidates)
    direction = _determine_direction(smc_candidates, snd_candidates, snapshot)
    setup_family = _determine_setup_family(smc_candidates, snd_candidates)
    patterns = _collect_patterns(smc_candidates, snd_candidates)

    smc_flags = _extract_smc_flags(smc_candidates)
    snd_flags = _extract_snd_flags(snd_candidates)

    session_context = _extract_session(
        smc_candidates, snd_candidates,
    )
    trend = snapshot.get("trend_direction")

    return TASignals(
        symbol=result.symbol,
        framework=framework,
        setup_family=setup_family,
        direction=direction,
        htf_timeframe=result.htf_timeframe,
        ltf_timeframe=result.ltf_timeframe,
        session_context=session_context,
        patterns_detected=patterns,
        has_bms=smc_flags.get("bms", False),
        has_choch=smc_flags.get("choch", False),
        has_sms=smc_flags.get("sms", False),
        has_liquidity_sweep=smc_flags.get("liquidity_swept", False),
        has_order_block=smc_flags.get("order_block", False),
        has_fvg=smc_flags.get("fvg", False),
        has_qml=snd_flags.get("qml", False),
        has_sr_flip=snd_flags.get("sr_flip", False),
        has_fakeout=snd_flags.get("fakeout", False),
        has_marubozu=snd_flags.get("marubozu", False),
        has_compression=snd_flags.get("compression", False),
        trend_direction=trend,
    )


def _determine_framework(
    smc: list[dict],
    snd: list[dict],
) -> Optional[str]:
    """Primary framework is whichever produced more candidates."""
    if smc and not snd:
        return "smc"
    if snd and not smc:
        return "snd"
    if smc and snd:
        return "smc" if len(smc) >= len(snd) else "snd"
    return None


def _determine_direction(
    smc: list[dict],
    snd: list[dict],
    snapshot: dict,
) -> Optional[str]:
    """Determine dominant direction from candidates.

    RAG uses lowercase: long/short/neutral.
    TA uses uppercase: BULLISH/BEARISH/NEUTRAL.
    """
    directions: list[str] = []
    for c in smc:
        d = c.get("direction", "")
        if d:
            directions.append(d)
    for c in snd:
        d = c.get("direction", "")
        if d:
            directions.append(d)

    if not directions:
        trend = snapshot.get("trend_direction", "")
        if trend:
            directions.append(trend)

    if not directions:
        return None

    bullish = sum(1 for d in directions if d.upper() == "BULLISH")
    bearish = sum(1 for d in directions if d.upper() == "BEARISH")

    if bullish > bearish:
        return "long"
    if bearish > bullish:
        return "short"
    return "neutral"


def _determine_setup_family(
    smc: list[dict],
    snd: list[dict],
) -> Optional[str]:
    """Determine the primary setup family from candidate patterns."""
    for c in smc:
        if c.get("order_block_upper") or c.get("order_block_lower"):
            return "order_block"
        if c.get("fvg_upper") or c.get("fvg_lower"):
            return "fair_value_gap"
        if c.get("liquidity_swept"):
            return "liquidity_sweep"
        pattern = c.get("pattern", "")
        if "TURTLE_SOUP" in pattern:
            return "turtle_soup"
        if "AMD" in pattern:
            return "amd"

    for c in snd:
        if c.get("qml_detected"):
            return "qml"
        if c.get("sr_flip_detected"):
            return "sr_flip"
        if c.get("rs_flip_detected"):
            return "rs_flip"
        if c.get("supply_zone_upper"):
            return "supply_zone"
        if c.get("demand_zone_upper"):
            return "demand_zone"
        if c.get("compression_detected"):
            return "compression"

    return None


def _collect_patterns(
    smc: list[dict],
    snd: list[dict],
) -> list[str]:
    """Collect all unique pattern names."""
    patterns: set[str] = set()
    for c in smc:
        p = c.get("pattern")
        if p:
            patterns.add(p)
    for c in snd:
        p = c.get("pattern")
        if p:
            patterns.add(p)
    return sorted(patterns)


def _extract_smc_flags(candidates: list[dict]) -> dict[str, bool]:
    """Extract boolean flags from SMC candidates."""
    flags: dict[str, bool] = {
        "bms": False,
        "choch": False,
        "sms": False,
        "liquidity_swept": False,
        "order_block": False,
        "fvg": False,
    }
    for c in candidates:
        if c.get("bms_detected"):
            flags["bms"] = True
        if c.get("choch_detected"):
            flags["choch"] = True
        if c.get("sms_detected"):
            flags["sms"] = True
        if c.get("liquidity_swept"):
            flags["liquidity_swept"] = True
        if c.get("order_block_upper") or c.get("order_block_lower"):
            flags["order_block"] = True
        if c.get("fvg_upper") or c.get("fvg_lower"):
            flags["fvg"] = True
    return flags


def _extract_snd_flags(candidates: list[dict]) -> dict[str, bool]:
    """Extract boolean flags from SnD candidates."""
    flags: dict[str, bool] = {
        "qml": False,
        "sr_flip": False,
        "fakeout": False,
        "marubozu": False,
        "compression": False,
    }
    for c in candidates:
        if c.get("qml_detected"):
            flags["qml"] = True
        if c.get("sr_flip_detected") or c.get("rs_flip_detected"):
            flags["sr_flip"] = True
        if c.get("fakeout_detected"):
            flags["fakeout"] = True
        if c.get("marubozu_detected"):
            flags["marubozu"] = True
        if c.get("compression_detected"):
            flags["compression"] = True
    return flags


def _extract_session(
    smc: list[dict],
    snd: list[dict],
) -> Optional[str]:
    """Extract session context from the most recent candidate."""
    for c in smc:
        s = c.get("session_context")
        if s:
            return s
    for c in snd:
        s = c.get("session_context")
        if s:
            return s
    return None
