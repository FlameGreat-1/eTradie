"""Extract RAG-relevant signals from Macro output.

Pure functions - no I/O, no side effects.
"""

from __future__ import annotations

from typing import Optional

from engine.shared.models.base import FrozenModel
from gateway.context.models import MacroResult


class MacroSignals(FrozenModel):
    """Extracted macro signals for RAG query construction."""

    macro_bias_usd: Optional[str] = None
    dxy_value: Optional[float] = None
    dxy_trend: Optional[str] = None
    cot_net_eur: Optional[float] = None
    cot_net_gbp: Optional[float] = None
    cot_net_jpy: Optional[float] = None
    fed_tone: Optional[str] = None
    ecb_tone: Optional[str] = None
    boe_tone: Optional[str] = None
    boj_tone: Optional[str] = None
    high_impact_events_within_24h: list[str] = []
    news_headlines: list[str] = []
    retail_sentiment_usd: Optional[float] = None
    risk_environment: Optional[str] = None
    has_rate_decision: bool = False
    has_nfp: bool = False
    has_cpi: bool = False


def extract_macro_signals(result: MacroResult) -> MacroSignals:
    """Extract RAG-relevant signals from the aggregated macro output."""
    cb_signals = _extract_central_bank(result.central_bank)
    cot_signals = _extract_cot(result.cot)
    econ_signals = _extract_economic(result.economic)
    calendar_signals = _extract_calendar(result.calendar)
    dxy_signals = _extract_dxy(result.dxy)
    news_signals = _extract_news(result.news)
    sentiment_signals = _extract_sentiment(result.sentiment)

    macro_bias_usd = _derive_usd_bias(cb_signals, econ_signals, dxy_signals)

    return MacroSignals(
        macro_bias_usd=macro_bias_usd,
        dxy_value=dxy_signals.get("value"),
        dxy_trend=dxy_signals.get("trend"),
        cot_net_eur=cot_signals.get("eur_net"),
        cot_net_gbp=cot_signals.get("gbp_net"),
        cot_net_jpy=cot_signals.get("jpy_net"),
        fed_tone=cb_signals.get("fed_tone"),
        ecb_tone=cb_signals.get("ecb_tone"),
        boe_tone=cb_signals.get("boe_tone"),
        boj_tone=cb_signals.get("boj_tone"),
        high_impact_events_within_24h=calendar_signals.get("high_impact_events", []),
        news_headlines=news_signals.get("headlines", []),
        retail_sentiment_usd=sentiment_signals.get("usd_long_pct"),
        risk_environment=sentiment_signals.get("risk_environment"),
        has_rate_decision=calendar_signals.get("has_rate_decision", False),
        has_nfp=calendar_signals.get("has_nfp", False),
        has_cpi=calendar_signals.get("has_cpi", False),
    )


def _extract_central_bank(data: Optional[dict]) -> dict:
    if not data:
        return {}

    signals: dict = {}
    for speech in data.get("speeches", []):
        bank = speech.get("bank", "").upper()
        tone = speech.get("tone", "NEUTRAL").upper()
        key = f"{bank.lower()}_tone"
        if key not in signals:
            signals[key] = tone

    for guidance in data.get("forward_guidance", []):
        bank = guidance.get("bank", "").upper()
        tone = guidance.get("tone", "NEUTRAL").upper()
        key = f"{bank.lower()}_tone"
        if key not in signals:
            signals[key] = tone

    for decision in data.get("rate_decisions", []):
        bank = decision.get("bank", "").upper()
        tone = decision.get("tone", "NEUTRAL").upper()
        key = f"{bank.lower()}_tone"
        signals[key] = tone

    return signals


def _extract_cot(data: Optional[dict]) -> dict:
    if not data:
        return {}

    signals: dict = {}
    for pos in data.get("latest_positions", []):
        currency = pos.get("currency", "").upper()
        net = pos.get("non_commercial_net", 0)
        if currency == "EUR":
            signals["eur_net"] = net
        elif currency == "GBP":
            signals["gbp_net"] = net
        elif currency == "JPY":
            signals["jpy_net"] = net

    return signals


def _extract_economic(data: Optional[dict]) -> dict:
    if not data:
        return {}

    signals: dict = {"surprise_directions": []}
    for release in data.get("releases", []):
        surprise_dir = release.get("surprise_direction", "")
        indicator = release.get("indicator", "")
        if surprise_dir and indicator:
            signals["surprise_directions"].append({
                "indicator": indicator,
                "direction": surprise_dir,
            })

    return signals


def _extract_calendar(data: Optional[dict]) -> dict:
    if not data:
        return {}

    signals: dict = {
        "high_impact_events": [],
        "has_rate_decision": False,
        "has_nfp": False,
        "has_cpi": False,
    }

    for event in data.get("events", []):
        impact = event.get("impact", "").upper()
        event_name = event.get("event_name", "")

        if impact == "HIGH":
            signals["high_impact_events"].append(event_name)

        name_upper = event_name.upper()
        if "RATE" in name_upper and "DECISION" in name_upper:
            signals["has_rate_decision"] = True
        if "NFP" in name_upper or "NON-FARM" in name_upper or "NONFARM" in name_upper:
            signals["has_nfp"] = True
        if "CPI" in name_upper or "CONSUMER PRICE" in name_upper:
            signals["has_cpi"] = True

    return signals


def _extract_dxy(data: Optional[dict]) -> dict:
    if not data:
        return {}

    latest = data.get("latest")
    if not latest:
        snapshots = data.get("snapshots", [])
        if snapshots:
            latest = snapshots[-1] if isinstance(snapshots[-1], dict) else {}

    if not latest:
        return {}

    return {
        "value": latest.get("dxy_value"),
        "trend": latest.get("trend"),
    }


def _extract_news(data: Optional[dict]) -> dict:
    if not data:
        return {}

    headlines: list[str] = []
    for item in data.get("items", [])[:10]:
        headline = item.get("headline", "")
        if headline:
            headlines.append(headline)

    return {"headlines": headlines}


def _extract_sentiment(data: Optional[dict]) -> dict:
    if not data:
        return {}

    signals: dict = {}
    sentiments = data.get("sentiments", [])
    for s in sentiments:
        currency = s.get("currency", "").upper()
        if currency == "USD":
            signals["usd_long_pct"] = s.get("long_percentage")

    return signals


def _derive_usd_bias(
    cb: dict,
    econ: dict,
    dxy: dict,
) -> Optional[str]:
    """Derive overall USD bias from central bank tone and economic data."""
    fed_tone = cb.get("fed_tone", "NEUTRAL").upper()

    if fed_tone == "HAWKISH":
        return "BULLISH"
    if fed_tone == "DOVISH":
        return "BEARISH"

    return "NEUTRAL"
