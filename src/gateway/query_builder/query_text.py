"""Build the semantic query_text string for RAG embedding search.

Combines TA signals and Macro signals into a natural-language query
that maximizes embedding similarity with relevant knowledge chunks.
"""

from __future__ import annotations

from gateway.query_builder.macro_extractor import MacroSignals
from gateway.query_builder.ta_extractor import TASignals


def build_query_text(
    ta: TASignals,
    macro: MacroSignals,
) -> str:
    """Build a semantic query string from extracted TA + Macro signals.

    The query is structured to hit the most relevant chunks in the
    vector store by including: symbol, direction, framework patterns,
    zone types, macro environment, and risk events.
    """
    parts: list[str] = []

    # Symbol and direction
    parts.append(ta.symbol)
    if ta.direction:
        direction_word = {
            "long": "bullish",
            "short": "bearish",
            "neutral": "neutral",
        }.get(ta.direction, ta.direction)
        parts.append(direction_word)

    # Framework and patterns
    if ta.framework:
        parts.append(ta.framework.upper())
    for pattern in ta.patterns_detected[:5]:
        parts.append(pattern.replace("_", " ").lower())

    # Structure events
    if ta.has_bms:
        parts.append("BOS")
    if ta.has_choch:
        parts.append("CHoCH")
    if ta.has_sms:
        parts.append("SMS")

    # Zones
    if ta.has_order_block:
        parts.append("order block")
    if ta.has_fvg:
        parts.append("FVG")
    if ta.has_liquidity_sweep:
        parts.append("liquidity sweep")
    if ta.has_qml:
        parts.append("QML")
    if ta.has_sr_flip:
        parts.append("SR flip")
    if ta.has_fakeout:
        parts.append("fakeout")
    if ta.has_compression:
        parts.append("compression")
    if ta.has_marubozu:
        parts.append("marubozu")

    # Timeframe
    if ta.htf_timeframe:
        parts.append(ta.htf_timeframe)

    # Session
    if ta.session_context:
        parts.append(f"{ta.session_context} session")

    # Macro environment
    if macro.macro_bias_usd:
        usd_word = {
            "BULLISH": "USD bullish",
            "BEARISH": "USD bearish",
            "NEUTRAL": "USD neutral",
        }.get(macro.macro_bias_usd, "")
        if usd_word:
            parts.append(usd_word)

    if macro.fed_tone:
        parts.append(f"Fed {macro.fed_tone.lower()}")
    if macro.ecb_tone:
        parts.append(f"ECB {macro.ecb_tone.lower()}")

    # Risk events
    if macro.has_nfp:
        parts.append("NFP")
    if macro.has_cpi:
        parts.append("CPI")
    if macro.has_rate_decision:
        parts.append("rate decision")
    for event in macro.high_impact_events_within_24h[:3]:
        parts.append(event)

    # COT positioning
    if macro.cot_net_eur is not None and abs(macro.cot_net_eur) > 20000:
        cot_dir = "long" if macro.cot_net_eur > 0 else "short"
        parts.append(f"EUR COT net {cot_dir}")

    return " ".join(parts)
