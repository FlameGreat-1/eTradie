"""Human-readable dashboard formatter.

Converts the raw LLM analysis output (stored as JSON in Postgres)
into clean, plain-text sections that non-technical users can read
on the dashboard. No JSON, no code, no technical jargon.

The React dashboard renders these text fields directly.
"""

from __future__ import annotations

from typing import Any, Optional


def format_for_dashboard(raw_output: dict, row: Any) -> dict[str, str]:
    """Convert raw analysis data into dashboard-friendly plain text.

    Args:
        raw_output: The raw_output JSON dict from the analysis_outputs table.
        row: The AnalysisOutputRow with top-level fields.

    Returns:
        Dict of plain-text sections keyed by display area.
    """
    direction = getattr(row, "direction", raw_output.get("direction", "NO SETUP"))
    pair = getattr(row, "pair", raw_output.get("pair", "Unknown"))
    grade = getattr(row, "setup_grade", raw_output.get("setup_grade", "REJECT"))
    score = getattr(row, "confluence_score", raw_output.get("confluence_score", {}))
    if isinstance(score, dict):
        score_val = score.get("score", 0.0)
    else:
        score_val = score

    return {
        "summary": _build_summary(pair, direction, grade, score_val),
        "reasoning": _build_reasoning(raw_output),
        "macro_summary": _build_macro_summary(raw_output),
        "technical_summary": _build_technical_summary(raw_output),
        "trade_plan": _build_trade_plan(raw_output, row),
        "confluence_breakdown": _build_confluence_breakdown(raw_output),
        "risk_info": _build_risk_info(raw_output, row),
        "event_warnings": _build_event_warnings(raw_output),
        "analyzed_by": _build_analyzed_by(raw_output, row),
    }


def _build_summary(pair: str, direction: str, grade: str, score: float) -> str:
    if direction == "NO SETUP":
        return f"{pair} - No Valid Setup Found - Score {score}/10"
    return f"{direction} {pair} - Grade {grade} - Score {score}/10"


def _build_reasoning(raw: dict) -> str:
    reasoning = raw.get("explainable_reasoning", "")
    if reasoning:
        return reasoning
    return "No detailed reasoning available for this analysis."


def _build_macro_summary(raw: dict) -> str:
    parts: list[str] = []

    macro = raw.get("macro_bias", {})
    if macro:
        base = macro.get("base_currency", {})
        quote = macro.get("quote_currency", {})
        if base:
            parts.append(f"Base currency: {base.get('bias', 'N/A')}")
        if quote:
            parts.append(f"Quote currency: {quote.get('bias', 'N/A')}")

    dxy = raw.get("dxy_bias", {})
    if dxy:
        parts.append(f"US Dollar (DXY): {dxy.get('direction', 'N/A')}")

    cot = raw.get("cot_signal", {})
    if cot and cot.get("summary"):
        cot_text = cot["summary"]
        if cot.get("extreme_flag"):
            cot_text += " (EXTREME POSITIONING WARNING)"
        parts.append(f"COT: {cot_text}")

    if not parts:
        return "Macro data was not available for this analysis."
    return "\n".join(parts)


def _build_technical_summary(raw: dict) -> str:
    parts: list[str] = []

    htf = raw.get("htf_bias", {})
    if htf:
        parts.append(f"HTF Bias: {htf.get('structure', 'N/A').replace('_', ' ').title()}")
        if htf.get("notes"):
            parts.append(f"  {htf['notes']}")

    mtf = raw.get("mtf_bias", {})
    if mtf:
        parts.append(f"MTF Bias: {mtf.get('structure', 'N/A').replace('_', ' ').title()}")
        if mtf.get("notes"):
            parts.append(f"  {mtf['notes']}")

    entry = raw.get("entry_setup", {})
    if entry and entry.get("type"):
        zone_type = entry["type"]
        quality = entry.get("quality", "N/A")
        bounds = entry.get("bounds", [])
        zone_text = f"Entry Setup: {zone_type} (Grade {quality})"
        if bounds and len(bounds) == 2:
            zone_text += f" at {bounds[0]} - {bounds[1]}"
        parts.append(zone_text)
    elif entry:
        parts.append("Entry Setup: No valid zone identified")

    wyckoff = raw.get("wyckoff_phase", {})
    if wyckoff and wyckoff.get("phase"):
        parts.append(f"Wyckoff Phase: {wyckoff['phase'].replace('_', ' ').title()}")

    if not parts:
        return "Technical structure data was not available."
    return "\n".join(parts)


def _build_trade_plan(raw: dict, row: Any) -> str:
    direction = getattr(row, "direction", raw.get("direction", "NO SETUP"))

    if direction == "NO SETUP":
        return "No trade. The analysis did not find a valid setup that meets all required conditions."

    parts: list[str] = []
    parts.append(f"Direction: {direction}")

    entry = raw.get("entry_zone", {})
    if entry.get("low") is not None and entry.get("high") is not None:
        parts.append(f"Entry Zone: {entry['low']} to {entry['high']}")

    sl = raw.get("stop_loss", {})
    if sl.get("price") is not None:
        sl_text = f"Stop Loss: {sl['price']}"
        if sl.get("reason"):
            sl_text += f" ({sl['reason']})"
        parts.append(sl_text)

    tps = raw.get("take_profits", [])
    for i, tp in enumerate(tps, 1):
        if tp.get("level") is not None:
            tp_text = f"Take Profit {i}: {tp['level']} (close {tp.get('size_pct', 0)}% of position)"
            if tp.get("basis"):
                tp_text += f" - {tp['basis']}"
            parts.append(tp_text)

    rr = raw.get("rr_ratio")
    if rr is not None:
        parts.append(f"Reward-to-Risk Ratio: 1:{rr:.1f}")

    if not parts:
        return "Trade plan details are not available."
    return "\n".join(parts)


def _build_confluence_breakdown(raw: dict) -> str:
    conf = raw.get("confluence_score", {})
    factors = conf.get("factors", [])

    if not factors:
        score = conf.get("score", 0)
        return f"Confluence Score: {score}/10 (factor breakdown not available)"

    parts: list[str] = []
    total = conf.get("score", 0)
    parts.append(f"Confluence Score: {total}/10")
    parts.append("")

    for f in factors:
        name = f.get("name", "Unknown")
        present = f.get("present", False)
        value = f.get("value", 0)
        notes = f.get("notes", "")

        status = "PRESENT" if present else "MISSING"
        icon = "+" if present else "-"
        line = f"  {icon} {name}: {status}"
        if value > 0:
            line += f" (+{value})"
        if notes:
            line += f" - {notes}"
        parts.append(line)

    return "\n".join(parts)


def _build_risk_info(raw: dict, row: Any) -> str:
    parts: list[str] = []

    confidence = getattr(row, "confidence", raw.get("confidence", "N/A"))
    grade = getattr(row, "setup_grade", raw.get("setup_grade", "N/A"))
    proceed = getattr(row, "proceed_to_module_b", raw.get("proceed_to_module_b", "NO"))

    parts.append(f"Confidence: {confidence}")
    parts.append(f"Setup Grade: {grade}")

    if grade in ("A+", "A"):
        parts.append("Risk Allocation: 1% of account")
    elif grade == "B":
        parts.append("Risk Allocation: 0.5% of account")
    else:
        parts.append("Risk Allocation: None (setup rejected)")

    if proceed == "YES":
        parts.append("Status: Approved for execution")
    else:
        parts.append("Status: Not approved for execution")

    return "\n".join(parts)


def _build_event_warnings(raw: dict) -> str:
    events = raw.get("event_risk", [])
    if not events:
        return "No high-impact economic events in the next 48 hours."

    parts: list[str] = ["Upcoming High-Impact Events:"]
    for e in events:
        event_name = e.get("event", "Unknown")
        event_time = e.get("time", "Time unknown")
        currency = e.get("currency", "")
        line = f"  - {event_name}"
        if currency:
            line += f" ({currency})"
        if event_time and event_time != "Time unknown":
            line += f" at {event_time}"
        parts.append(line)

    return "\n".join(parts)


def _build_analyzed_by(raw: dict, row: Any) -> str:
    provider = getattr(row, "llm_provider", raw.get("_llm_provider", "Unknown"))
    model = getattr(row, "llm_model", raw.get("_llm_model", "Unknown"))
    duration = getattr(row, "duration_ms", 0)

    provider_names = {
        "anthropic": "Anthropic Claude",
        "openai": "OpenAI GPT",
        "gemini": "Google Gemini",
        "self_hosted": "Self-Hosted Model",
    }
    display_provider = provider_names.get(provider, provider)

    text = f"Analyzed by: {display_provider} ({model})"
    if duration > 0:
        text += f" in {duration / 1000:.1f} seconds"
    return text
