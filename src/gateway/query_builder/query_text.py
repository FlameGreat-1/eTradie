"""Build the semantic query_text string for RAG embedding search.

Combines TA signals and Macro signals into a natural-language query
that maximizes embedding similarity with relevant knowledge chunks.

CRITICAL: No artificial limits on any signal. Every signal present
in the TA+Macro output must be represented so the RAG retrieves
ALL relevant rules from the knowledge base.
"""

from __future__ import annotations

from gateway.query_builder.macro_extractor import MacroSignals
from gateway.query_builder.ta_extractor import TASignals


def build_query_text(
    ta: TASignals,
    macro: MacroSignals,
) -> str:
    """Build a semantic query string from ALL extracted TA + Macro signals."""
    parts: list[str] = []

    _add_ta_signals(parts, ta)
    _add_macro_signals(parts, macro)

    return " ".join(parts)


def _add_ta_signals(parts: list[str], ta: TASignals) -> None:
    """Add ALL TA signals to the query."""
    # Symbol and direction
    parts.append(ta.symbol)
    if ta.direction:
        direction_word = {
            "long": "bullish",
            "short": "bearish",
            "neutral": "neutral",
        }.get(ta.direction, ta.direction)
        parts.append(direction_word)

    # Trend
    if ta.trend_direction and ta.trend_direction != "NEUTRAL":
        parts.append(f"trend {ta.trend_direction.lower()}")

    # Framework
    if ta.framework:
        parts.append(ta.framework.upper())

    # ALL patterns - no limit
    for pattern in ta.patterns_detected:
        parts.append(pattern.replace("_", " ").lower())

    # ALL setup families - no limit
    for family in ta.setup_families:
        parts.append(family.replace("_", " "))

    # Structure events
    if ta.has_bms:
        parts.append("BOS break of structure")
    if ta.has_choch:
        parts.append("CHoCH change of character")
    if ta.has_sms:
        parts.append("SMS shift in market structure")

    # SMC zones and events
    if ta.has_order_block:
        parts.append("order block")
    if ta.has_fvg:
        parts.append("fair value gap FVG")
    if ta.has_liquidity_sweep:
        parts.append("liquidity sweep")
    if ta.has_inducement_cleared:
        parts.append("inducement cleared")
    if ta.has_displacement:
        parts.append("displacement")

    # SnD zones and events
    if ta.has_qml:
        parts.append("QML quasi modo level")
    if ta.has_sr_flip:
        parts.append("SR flip support resistance flip")
    if ta.has_rs_flip:
        parts.append("RS flip resistance support flip")
    if ta.has_mpl:
        parts.append("MPL mini price level")
    if ta.has_fakeout:
        parts.append("fakeout")
    if ta.has_marubozu:
        parts.append("marubozu")
    if ta.has_compression:
        parts.append("compression")

    # Previous levels
    if ta.has_previous_levels:
        parts.append("previous highs lows")
        if ta.previous_highs_count > 0:
            parts.append(f"{ta.previous_highs_count} previous highs")
        if ta.previous_lows_count > 0:
            parts.append(f"{ta.previous_lows_count} previous lows")

    # Fibonacci
    if ta.has_fib_confluence:
        parts.append("fibonacci confluence")
        for level in ta.fib_levels:
            parts.append(f"fib {level}")

    # Timeframes
    for htf in ta.htf_timeframes:
        parts.append(htf)
    for ltf in ta.ltf_timeframes:
        parts.append(ltf)

    # Session
    if ta.session_context:
        parts.append(f"{ta.session_context} session")


def _add_macro_signals(parts: list[str], macro: MacroSignals) -> None:
    """Add ALL macro signals to the query."""
    # USD bias
    if macro.macro_bias_usd:
        usd_word = {
            "BULLISH": "USD bullish strong dollar",
            "BEARISH": "USD bearish weak dollar",
            "NEUTRAL": "USD neutral",
        }.get(macro.macro_bias_usd, "")
        if usd_word:
            parts.append(usd_word)

    # ALL central bank tones
    if macro.fed_tone:
        parts.append(f"Fed {macro.fed_tone.lower()}")
    if macro.ecb_tone:
        parts.append(f"ECB {macro.ecb_tone.lower()}")
    if macro.boe_tone:
        parts.append(f"BOE {macro.boe_tone.lower()}")
    if macro.boj_tone:
        parts.append(f"BOJ {macro.boj_tone.lower()}")

    # Rate change
    if macro.has_rate_change:
        parts.append(f"{macro.rate_change_bank} rate {macro.rate_change_direction}")

    # DXY
    if macro.dxy_value is not None:
        parts.append(f"DXY {macro.dxy_value}")
    if macro.dxy_trend:
        parts.append(f"DXY trend {macro.dxy_trend}")

    # ALL calendar events - no limit
    if macro.has_nfp:
        parts.append("NFP non-farm payrolls")
    if macro.has_cpi:
        parts.append("CPI consumer price index inflation")
    if macro.has_ppi:
        parts.append("PPI producer price index")
    if macro.has_gdp:
        parts.append("GDP gross domestic product")
    if macro.has_rate_decision:
        parts.append("rate decision interest rate")
    if macro.has_employment:
        parts.append("employment unemployment")
    if macro.has_pmi:
        parts.append("PMI purchasing managers index")
    if macro.has_retail_sales:
        parts.append("retail sales")
    if macro.has_cb_speech:
        parts.append("central bank speech")

    for event in macro.high_impact_events_within_24h:
        parts.append(event)

    # ALL COT positioning - no limit
    _add_cot_signal(parts, "EUR", macro.cot_net_eur)
    _add_cot_signal(parts, "GBP", macro.cot_net_gbp)
    _add_cot_signal(parts, "JPY", macro.cot_net_jpy)
    _add_cot_signal(parts, "AUD", macro.cot_net_aud)
    _add_cot_signal(parts, "CAD", macro.cot_net_cad)
    _add_cot_signal(parts, "NZD", macro.cot_net_nzd)
    _add_cot_signal(parts, "CHF", macro.cot_net_chf)

    # Economic surprises
    for surprise in macro.economic_surprises:
        indicator = surprise.get("indicator_name") or surprise.get("indicator", "")
        direction = surprise.get("direction", "")
        impact = surprise.get("impact", "")
        if indicator and direction:
            if impact and impact.upper() == "HIGH":
                parts.append(f"{indicator} {direction.lower()} surprise")

    # Intermarket
    if macro.vix is not None and macro.vix > 25:
        parts.append(f"VIX elevated {macro.vix}")
    if macro.yield_curve_inverted:
        parts.append("yield curve inverted recession signal")
    if macro.gold_price is not None:
        parts.append("gold")
    if macro.oil_price is not None:
        parts.append("oil")

    # Retail sentiment crowding
    for currency, long_pct in macro.retail_sentiment.items():
        if long_pct is not None:
            if long_pct > 70:
                parts.append(f"{currency} retail crowded long {long_pct}%")
            elif long_pct < 30:
                parts.append(f"{currency} retail crowded short {100 - long_pct}%")

    # News headlines
    for headline in macro.news_headlines:
        parts.append(headline)


def _add_cot_signal(
    parts: list[str],
    currency: str,
    net: float | None,
) -> None:
    """Add COT signal for any currency with significant positioning."""
    if net is None:
        return
    if abs(net) < 5000:
        return
    cot_dir = "net long" if net > 0 else "net short"
    parts.append(f"{currency} COT {cot_dir} {int(net)}")
