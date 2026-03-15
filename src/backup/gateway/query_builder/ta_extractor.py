"""Extract RAG-relevant signals from TA output.

Pure functions - no I/O, no side effects.
Captures ALL signals from TA candidates without truncation or omission.
"""

from __future__ import annotations

from typing import Optional

from engine.shared.models.base import FrozenModel
from gateway.context.models import TASymbolResult


class TASignals(FrozenModel):
    """Extracted TA signals for a single symbol.

    Every boolean flag and list captures ALL detected signals
    without artificial limits, so the RAG query can retrieve
    every relevant rule from the knowledge base.
    """

    symbol: str
    framework: Optional[str] = None
    setup_families: list[str] = []
    direction: Optional[str] = None
    htf_timeframes: list[str] = []
    ltf_timeframes: list[str] = []
    overall_trend: Optional[str] = None
    session_context: Optional[str] = None
    patterns_detected: list[str] = []
    fib_levels: list[str] = []
    trend_direction: Optional[str] = None

    # SMC flags
    has_bms: bool = False
    has_choch: bool = False
    has_sms: bool = False
    has_liquidity_sweep: bool = False
    has_order_block: bool = False
    has_fvg: bool = False
    has_inducement_cleared: bool = False
    has_displacement: bool = False

    # SnD flags
    has_qml: bool = False
    has_sr_flip: bool = False
    has_rs_flip: bool = False
    has_mpl: bool = False
    has_fakeout: bool = False
    has_marubozu: bool = False
    has_compression: bool = False
    has_previous_levels: bool = False
    has_fib_confluence: bool = False
    previous_highs_count: int = 0
    previous_lows_count: int = 0


def extract_ta_signals(result: TASymbolResult) -> TASignals:
    """Extract ALL RAG-relevant signals from a single symbol's TA result."""
    if result.status != "success":
        return TASignals(symbol=result.symbol)

    smc_candidates = result.smc_candidates
    snd_candidates = result.snd_candidates
    # Merge all per-timeframe snapshots into a single dict for signal extraction
    snapshot: dict = {}
    for tf_key, tf_snap in result.snapshots.items():
        snapshot = tf_snap  # Use the last (lowest) TF snapshot for direction fallback
        break  # Use highest TF snapshot (first in dict) for trend

    framework = _determine_framework(smc_candidates, snd_candidates)
    direction = _determine_direction(smc_candidates, snd_candidates, snapshot)
    setup_families = _collect_all_setup_families(smc_candidates, snd_candidates)
    patterns = _collect_patterns(smc_candidates, snd_candidates)
    fib_levels = _collect_fib_levels(smc_candidates, snd_candidates)

    smc_flags = _extract_smc_flags(smc_candidates)
    snd_flags = _extract_snd_flags(snd_candidates)

    session_context = _extract_session(smc_candidates, snd_candidates)

    prev_highs, prev_lows = _extract_previous_level_counts(snd_candidates)

    return TASignals(
        symbol=result.symbol,
        framework=framework,
        setup_families=setup_families,
        direction=direction,
        htf_timeframes=result.htf_timeframes,
        ltf_timeframes=result.ltf_timeframes,
        overall_trend=result.overall_trend,
        session_context=session_context,
        patterns_detected=patterns,
        fib_levels=fib_levels,
        trend_direction=result.overall_trend,
        has_bms=smc_flags.get("bms", False),
        has_choch=smc_flags.get("choch", False),
        has_sms=smc_flags.get("sms", False),
        has_liquidity_sweep=smc_flags.get("liquidity_swept", False),
        has_order_block=smc_flags.get("order_block", False),
        has_fvg=smc_flags.get("fvg", False),
        has_inducement_cleared=smc_flags.get("inducement_cleared", False),
        has_displacement=smc_flags.get("displacement", False),
        has_qml=snd_flags.get("qml", False),
        has_sr_flip=snd_flags.get("sr_flip", False),
        has_rs_flip=snd_flags.get("rs_flip", False),
        has_mpl=snd_flags.get("mpl", False),
        has_fakeout=snd_flags.get("fakeout", False),
        has_marubozu=snd_flags.get("marubozu", False),
        has_compression=snd_flags.get("compression", False),
        has_previous_levels=prev_highs > 0 or prev_lows > 0,
        has_fib_confluence=len(fib_levels) > 0,
        previous_highs_count=prev_highs,
        previous_lows_count=prev_lows,
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


def _collect_all_setup_families(
    smc: list[dict],
    snd: list[dict],
) -> list[str]:
    """Collect ALL setup families present across all candidates.

    Returns every unique family so the RAG can retrieve rules
    for every setup type detected, not just the first one.
    """
    families: set[str] = set()

    for c in smc:
        if c.get("order_block_upper") or c.get("order_block_lower"):
            families.add("order_block")
        if c.get("fvg_upper") or c.get("fvg_lower"):
            families.add("fair_value_gap")
        if c.get("liquidity_swept"):
            families.add("liquidity_sweep")
        if c.get("inducement_cleared"):
            families.add("inducement")
        pattern = c.get("pattern", "")
        if "TURTLE_SOUP" in pattern:
            families.add("turtle_soup")
        if "AMD" in pattern:
            families.add("amd")
        if "SH_BMS_RTO" in pattern:
            families.add("bms_rto")
        if "SMS_BMS_RTO" in pattern:
            families.add("sms_rto")

    for c in snd:
        if c.get("qml_detected"):
            families.add("qml")
        if c.get("sr_flip_detected"):
            families.add("sr_flip")
        if c.get("rs_flip_detected"):
            families.add("rs_flip")
        if c.get("mpl_detected"):
            families.add("mpl")
        if c.get("supply_zone_upper"):
            families.add("supply_zone")
        if c.get("demand_zone_upper"):
            families.add("demand_zone")
        if c.get("compression_detected"):
            families.add("compression")
        if c.get("fakeout_detected"):
            families.add("fakeout")
        pattern = c.get("pattern", "")
        if "FAKEOUT_KING" in pattern:
            families.add("fakeout_king")
        if "QML_KILLER" in pattern:
            families.add("qml_killer")
        if "QML_TRIPLE" in pattern:
            families.add("triple_fakeout")
        if "SOP" in pattern:
            families.add("sop")
        if "CONTINUATION" in pattern:
            families.add("continuation")

    return sorted(families)


def _collect_patterns(
    smc: list[dict],
    snd: list[dict],
) -> list[str]:
    """Collect ALL unique pattern names without any limit."""
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


def _collect_fib_levels(
    smc: list[dict],
    snd: list[dict],
) -> list[str]:
    """Collect ALL Fibonacci levels detected across candidates."""
    levels: set[str] = set()
    for c in smc:
        fib = c.get("fib_level")
        if fib:
            levels.add(fib)
    for c in snd:
        fib = c.get("fib_level")
        if fib:
            levels.add(fib)
    return sorted(levels)


def _extract_smc_flags(candidates: list[dict]) -> dict[str, bool]:
    """Extract ALL boolean flags from SMC candidates."""
    flags: dict[str, bool] = {
        "bms": False,
        "choch": False,
        "sms": False,
        "liquidity_swept": False,
        "order_block": False,
        "fvg": False,
        "inducement_cleared": False,
        "displacement": False,
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
        if c.get("inducement_cleared"):
            flags["inducement_cleared"] = True
        displacement = c.get("displacement_pips")
        if displacement is not None and displacement > 0:
            flags["displacement"] = True
    return flags


def _extract_snd_flags(candidates: list[dict]) -> dict[str, bool]:
    """Extract ALL boolean flags from SnD candidates."""
    flags: dict[str, bool] = {
        "qml": False,
        "sr_flip": False,
        "rs_flip": False,
        "mpl": False,
        "fakeout": False,
        "marubozu": False,
        "compression": False,
    }
    for c in candidates:
        if c.get("qml_detected"):
            flags["qml"] = True
        if c.get("sr_flip_detected"):
            flags["sr_flip"] = True
        if c.get("rs_flip_detected"):
            flags["rs_flip"] = True
        if c.get("mpl_detected"):
            flags["mpl"] = True
        if c.get("fakeout_detected"):
            flags["fakeout"] = True
        if c.get("marubozu_detected"):
            flags["marubozu"] = True
        if c.get("compression_detected"):
            flags["compression"] = True
    return flags


def _extract_previous_level_counts(
    snd: list[dict],
) -> tuple[int, int]:
    """Extract max previous highs/lows counts from SnD candidates."""
    max_highs = 0
    max_lows = 0
    for c in snd:
        highs = c.get("previous_highs_count", 0)
        lows = c.get("previous_lows_count", 0)
        if highs > max_highs:
            max_highs = highs
        if lows > max_lows:
            max_lows = lows
    return max_highs, max_lows


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
