"""Extract RAG-relevant signals from Macro output.

Pure functions - no I/O, no side effects.
Captures ALL signals from macro data without truncation or omission.
"""

from __future__ import annotations

from typing import Optional

from engine.shared.models.base import FrozenModel
from gateway.context.models import MacroResult


class MacroSignals(FrozenModel):
    """Extracted macro signals for RAG query construction.

    Every list and field captures ALL available data without
    artificial limits, so the RAG query can retrieve every
    relevant rule from the knowledge base.
    """

    # USD bias
    macro_bias_usd: Optional[str] = None

    # DXY
    dxy_value: Optional[float] = None
    dxy_trend: Optional[str] = None

    # COT - all currencies
    cot_net_eur: Optional[float] = None
    cot_net_gbp: Optional[float] = None
    cot_net_jpy: Optional[float] = None
    cot_net_aud: Optional[float] = None
    cot_net_cad: Optional[float] = None
    cot_net_nzd: Optional[float] = None
    cot_net_chf: Optional[float] = None

    # Central bank tones
    fed_tone: Optional[str] = None
    ecb_tone: Optional[str] = None
    boe_tone: Optional[str] = None
    boj_tone: Optional[str] = None
    has_rate_change: bool = False
    rate_change_bank: Optional[str] = None
    rate_change_direction: Optional[str] = None

    # Calendar - no limits
    high_impact_events_within_24h: list[str] = []
    has_rate_decision: bool = False
    has_nfp: bool = False
    has_cpi: bool = False
    has_ppi: bool = False
    has_gdp: bool = False
    has_employment: bool = False
    has_pmi: bool = False
    has_retail_sales: bool = False
    has_cb_speech: bool = False

    # News - no limits
    news_headlines: list[str] = []

    # Economic releases
    economic_surprises: list[dict] = []

    # Sentiment - all currencies
    retail_sentiment: dict[str, float] = {}
    risk_environment: Optional[str] = None

    # Intermarket
    gold_price: Optional[float] = None
    oil_price: Optional[float] = None
    us2y_yield: Optional[float] = None
    us10y_yield: Optional[float] = None
    us30y_yield: Optional[float] = None
    sp500: Optional[float] = None
    vix: Optional[float] = None
    yield_curve_inverted: Optional[bool] = None


def extract_macro_signals(result: MacroResult) -> MacroSignals:
    """Extract ALL RAG-relevant signals from the aggregated macro output."""
    cb_signals = _extract_central_bank(result.central_bank)
    cot_signals = _extract_cot(result.cot)
    econ_signals = _extract_economic(result.economic)
    calendar_signals = _extract_calendar(result.calendar)
    dxy_signals = _extract_dxy(result.dxy)
    news_signals = _extract_news(result.news)
    sentiment_signals = _extract_sentiment(result.sentiment)
    intermarket_signals = _extract_intermarket(result.intermarket)

    macro_bias_usd = _derive_usd_bias(cb_signals, econ_signals, dxy_signals)

    yield_inverted = None
    us2y = intermarket_signals.get("us2y_yield")
    us10y = intermarket_signals.get("us10y_yield")
    if us2y is not None and us10y is not None:
        yield_inverted = us2y > us10y

    return MacroSignals(
        macro_bias_usd=macro_bias_usd,
        dxy_value=dxy_signals.get("value"),
        dxy_trend=dxy_signals.get("trend"),
        cot_net_eur=cot_signals.get("eur_net"),
        cot_net_gbp=cot_signals.get("gbp_net"),
        cot_net_jpy=cot_signals.get("jpy_net"),
        cot_net_aud=cot_signals.get("aud_net"),
        cot_net_cad=cot_signals.get("cad_net"),
        cot_net_nzd=cot_signals.get("nzd_net"),
        cot_net_chf=cot_signals.get("chf_net"),
        fed_tone=cb_signals.get("fed_tone"),
        ecb_tone=cb_signals.get("ecb_tone"),
        boe_tone=cb_signals.get("boe_tone"),
        boj_tone=cb_signals.get("boj_tone"),
        has_rate_change=cb_signals.get("has_rate_change", False),
        rate_change_bank=cb_signals.get("rate_change_bank"),
        rate_change_direction=cb_signals.get("rate_change_direction"),
        high_impact_events_within_24h=calendar_signals.get("high_impact_events", []),
        has_rate_decision=calendar_signals.get("has_rate_decision", False),
        has_nfp=calendar_signals.get("has_nfp", False),
        has_cpi=calendar_signals.get("has_cpi", False),
        has_ppi=calendar_signals.get("has_ppi", False),
        has_gdp=calendar_signals.get("has_gdp", False),
        has_employment=calendar_signals.get("has_employment", False),
        has_pmi=calendar_signals.get("has_pmi", False),
        has_retail_sales=calendar_signals.get("has_retail_sales", False),
        has_cb_speech=calendar_signals.get("has_cb_speech", False),
        news_headlines=news_signals.get("headlines", []),
        economic_surprises=econ_signals.get("surprise_directions", []),
        retail_sentiment=sentiment_signals.get("all_currencies", {}),
        risk_environment=sentiment_signals.get("risk_environment"),
        gold_price=intermarket_signals.get("gold_price"),
        oil_price=intermarket_signals.get("oil_price"),
        us2y_yield=us2y,
        us10y_yield=us10y,
        us30y_yield=intermarket_signals.get("us30y_yield"),
        sp500=intermarket_signals.get("sp500"),
        vix=intermarket_signals.get("vix"),
        yield_curve_inverted=yield_inverted,
    )


def _extract_central_bank(data: Optional[dict]) -> dict:
    if not data:
        return {}

    signals: dict = {"has_rate_change": False}

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

        rate_change = decision.get("rate_change_bps") or decision.get("change")
        if rate_change is not None and rate_change != 0:
            signals["has_rate_change"] = True
            signals["rate_change_bank"] = bank
            signals["rate_change_direction"] = "hike" if rate_change > 0 else "cut"

    return signals


def _extract_cot(data: Optional[dict]) -> dict:
    if not data:
        return {}

    signals: dict = {}
    currency_map = {
        "EUR": "eur_net",
        "GBP": "gbp_net",
        "JPY": "jpy_net",
        "AUD": "aud_net",
        "CAD": "cad_net",
        "NZD": "nzd_net",
        "CHF": "chf_net",
    }

    for pos in data.get("latest_positions", []):
        currency = pos.get("currency", "").upper()
        net = pos.get("non_commercial_net", 0)
        key = currency_map.get(currency)
        if key:
            signals[key] = net

    return signals


def _extract_economic(data: Optional[dict]) -> dict:
    if not data:
        return {}

    signals: dict = {"surprise_directions": []}
    for release in data.get("releases", []):
        surprise_dir = release.get("surprise_direction", "")
        indicator = release.get("indicator", "")
        indicator_name = release.get("indicator_name", "")
        currency = release.get("currency", "")
        impact = release.get("impact", "")
        if surprise_dir and indicator:
            signals["surprise_directions"].append({
                "indicator": indicator,
                "indicator_name": indicator_name,
                "direction": surprise_dir,
                "currency": currency,
                "impact": impact,
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
        "has_ppi": False,
        "has_gdp": False,
        "has_employment": False,
        "has_pmi": False,
        "has_retail_sales": False,
        "has_cb_speech": False,
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
        if "CPI" in name_upper or "CONSUMER PRICE INDEX" in name_upper:
            signals["has_cpi"] = True
        if "PPI" in name_upper or "PRODUCER PRICE" in name_upper:
            signals["has_ppi"] = True
        if "GDP" in name_upper or "GROSS DOMESTIC" in name_upper:
            signals["has_gdp"] = True
        if "EMPLOYMENT" in name_upper or "UNEMPLOYMENT" in name_upper or "JOBLESS" in name_upper:
            signals["has_employment"] = True
        if "PMI" in name_upper or "PURCHASING MANAGER" in name_upper:
            signals["has_pmi"] = True
        if "RETAIL SALES" in name_upper:
            signals["has_retail_sales"] = True
        if "SPEECH" in name_upper or "SPEAKS" in name_upper or "TESTIMONY" in name_upper:
            signals["has_cb_speech"] = True

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
    """Extract ALL news headlines without any limit."""
    if not data:
        return {}

    headlines: list[str] = []
    for item in data.get("items", []):
        headline = item.get("headline", "")
        if headline:
            headlines.append(headline)

    return {"headlines": headlines}


def _extract_sentiment(data: Optional[dict]) -> dict:
    if not data:
        return {}

    signals: dict = {"all_currencies": {}}
    sentiments = data.get("sentiments", [])
    for s in sentiments:
        currency = s.get("currency", "").upper()
        long_pct = s.get("long_percentage")
        if currency and long_pct is not None:
            signals["all_currencies"][currency] = long_pct

    return signals


def _extract_intermarket(data: Optional[dict]) -> dict:
    """Extract ALL intermarket data."""
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
        "gold_price": latest.get("gold_price"),
        "silver_price": latest.get("silver_price"),
        "oil_price": latest.get("oil_price"),
        "us2y_yield": latest.get("us2y_yield"),
        "us10y_yield": latest.get("us10y_yield"),
        "us30y_yield": latest.get("us30y_yield"),
        "sp500": latest.get("sp500"),
        "vix": latest.get("vix"),
        "dxy_value": latest.get("dxy_value"),
    }


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
