"""Test data factories for the eTradie Engine test suite.

Every factory produces real Pydantic domain models that match
the production code in src/engine/ exactly. No stale fields,
no placeholder values, no mismatched signatures.

Usage:
    from tests.factories import make_candle, make_candle_sequence
    seq = make_candle_sequence(count=50, trend="up", symbol="EURUSD")
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Optional

from engine.ta.constants import Direction, Timeframe
from engine.ta.models.candle import Candle, CandleSequence


# ---------------------------------------------------------------------------
# Candle factories
# ---------------------------------------------------------------------------

def make_candle(
    timestamp: Optional[datetime] = None,
    open: float = 1.0,
    high: float = 1.05,
    low: float = 0.95,
    close: float = 1.02,
    volume: float = 1000.0,
    timeframe: Timeframe = Timeframe.H1,
    symbol: str = "EURUSD",
) -> Candle:
    """Create a single Candle matching the real Candle model."""
    if timestamp is None:
        timestamp = datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return Candle(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def make_candle_sequence(
    count: int = 100,
    timeframe: Timeframe = Timeframe.H1,
    start_time: Optional[datetime] = None,
    symbol: str = "EURUSD",
    trend: str = "up",
    base_price: float = 1.10000,
) -> CandleSequence:
    """Create a CandleSequence with realistic price action.

    Args:
        count: Number of candles.
        timeframe: Timeframe for all candles.
        start_time: Timestamp of the first candle.
        symbol: Symbol for all candles.
        trend: "up", "down", or "range".
        base_price: Starting price level.

    Returns:
        CandleSequence matching the real model (sorted, validated).
    """
    if start_time is None:
        start_time = datetime.now(UTC) - timedelta(hours=count)
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)

    candles: list[Candle] = []

    for i in range(count):
        if trend == "up":
            open_price = base_price + (i * 0.00100)
            close_price = open_price + 0.00050
        elif trend == "down":
            open_price = base_price - (i * 0.00100)
            close_price = open_price - 0.00050
        else:  # range
            open_price = base_price + ((-1) ** i) * 0.00050
            close_price = base_price - ((-1) ** i) * 0.00050

        high_price = max(open_price, close_price) + 0.00020
        low_price = min(open_price, close_price) - 0.00020

        candle = Candle(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=start_time + timedelta(hours=i),
            open=round(open_price, 5),
            high=round(high_price, 5),
            low=round(low_price, 5),
            close=round(close_price, 5),
            volume=float(1000 + i * 10),
        )
        candles.append(candle)

    return CandleSequence(symbol=symbol, timeframe=timeframe, candles=candles)


# ---------------------------------------------------------------------------
# TA result factory (matches TAOrchestrator._build_result output)
# ---------------------------------------------------------------------------

def make_ta_result(
    symbol: str = "EURUSD",
    status: str = "success",
    overall_trend: str = "BULLISH",
    smc_count: int = 1,
    snd_count: int = 0,
) -> dict:
    """Create a TA result dict matching TAOrchestrator._build_result output."""
    smc_candidates = [
        {
            "symbol": symbol,
            "pattern": "TURTLE_SOUP_LONG",
            "direction": "BULLISH",
            "entry_price": 1.10000,
            "stop_loss": 1.09500,
            "take_profit": 1.11500,
            "timeframe": "H4",
        }
    ] * smc_count

    snd_candidates = [
        {
            "symbol": symbol,
            "pattern": "QML_BASELINE",
            "direction": "BULLISH",
            "entry_price": 1.10000,
            "stop_loss": 1.09500,
            "take_profit": 1.11500,
            "timeframe": "H4",
        }
    ] * snd_count

    return {
        "status": status,
        "symbol": symbol,
        "htf_timeframes": ["W1", "D1", "H4", "H1"],
        "ltf_timeframes": ["M30", "M15", "M5", "M1"],
        "snapshots": {},
        "smc_candidates": smc_candidates,
        "snd_candidates": snd_candidates,
        "smc_candidates_count": smc_count,
        "snd_candidates_count": snd_count,
        "alignment": {},
        "overall_trend": overall_trend,
        "error": None,
    }


# ---------------------------------------------------------------------------
# Macro result factory (matches /internal/macro/collect response)
# ---------------------------------------------------------------------------

def make_macro_result(
    has_central_bank: bool = True,
    has_cot: bool = True,
    has_calendar: bool = True,
) -> dict:
    """Create a macro result dict matching the Python engine response."""
    return {
        "central_bank": {"speeches": [], "rate_decisions": []} if has_central_bank else None,
        "cot": {"latest_positions": [], "extremes_flagged": []} if has_cot else None,
        "economic": {"releases": []},
        "news": {"articles": []},
        "calendar": {"events": []} if has_calendar else None,
        "dxy": {"latest": {"dxy_value": 104.5, "dxy_momentum": "BULLISH"}},
        "intermarket": {"snapshots": []},
        "sentiment": {"risk_environment": "RISK_ON"},
        "errors": {},
    }
