from unittest.mock import AsyncMock

import pytest

from engine.macro.collectors.base import MacroCollector
from engine.macro.collectors.central_bank import CentralBankCollector
from engine.macro.collectors.cot import COTCollector
from engine.macro.collectors.dxy import DXYCollector
from engine.macro.collectors.economic import EconomicDataCollector
from engine.macro.collectors.events import EventCalendarCollector
from engine.macro.collectors.intermarket import IntermarketCollector
from engine.macro.collectors.news import NewsSentimentCollector


@pytest.fixture
def mock_cache():
    cache = AsyncMock()
    cache.get.return_value = None  # Force miss to test underlying logic
    return cache


@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    return provider


@pytest.mark.asyncio
async def test_central_bank_collector(mock_cache, mock_provider):
    """Test central bank collector with valid text for LLM extraction."""
    collector = CentralBankCollector(cache=mock_cache)
    collector.get_provider = lambda name: mock_provider
    
    mock_provider.fetch_latest_statement.return_value = "The committee decided to raise rates to combat inflation."
    
    # We won't test the actual LLM extraction here (it's unit testing)
    # We just ensure the collector builds the right structure.
    result = await collector.collect("USD")
    
    assert "central_bank" in result
    assert "error" not in result["central_bank"]


@pytest.mark.asyncio
async def test_cot_collector(mock_cache, mock_provider):
    """Test COT positioning aggregation."""
    collector = COTCollector(cache=mock_cache)
    collector.get_provider = lambda name: mock_provider
    
    mock_provider.fetch_cot_report.return_value = {
        "non_commercial_long": 150000,
        "non_commercial_short": 50000,
        "change_long": 10000,
        "change_short": -5000,
    }
    
    result = await collector.collect("EUR")
    
    assert "cot" in result
    data = result["cot"]
    assert "net_position" in data
    assert data["net_position"] > 0  # Net long
    assert data["bias"] == "BULLISH"


@pytest.mark.asyncio
async def test_dxy_collector(mock_cache, mock_provider):
    """Test DXY trend analysis from mock price data."""
    collector = DXYCollector(cache=mock_cache)
    collector.get_provider = lambda name: mock_provider
    
    mock_provider.get_historical_candles.return_value = [
        # simulate an uptrend
        {"close": 100.0}, {"close": 101.0}, {"close": 102.0}, {"close": 103.0}
    ]
    
    result = await collector.collect("USD")
    
    assert "dxy" in result
    assert result["dxy"]["trend"] == "BULLISH"


@pytest.mark.asyncio
async def test_event_calendar_collector(mock_cache, mock_provider):
    """Test calendar filters only high impact events."""
    collector = EventCalendarCollector(cache=mock_cache)
    collector.get_provider = lambda name: mock_provider
    
    mock_provider.fetch_upcoming_events.return_value = [
        {"event": "Low impact detail", "impact": "LOW"},
        {"event": "NFP Report", "impact": "HIGH"},
    ]
    
    result = await collector.collect("USD")
    
    assert "events" in result
    events = result["events"]
    assert len(events) == 1
    assert events[0]["event"] == "NFP Report"


@pytest.mark.asyncio
async def test_collector_provider_failure(mock_cache, mock_provider):
    """Test collectors degrade gracefully when API fails."""
    collector = DXYCollector(cache=mock_cache)
    collector.get_provider = lambda name: mock_provider
    
    mock_provider.get_historical_candles.side_effect = Exception("API Error")
    
    result = await collector.collect("USD")
    
    assert "dxy" in result
    assert "error" in result["dxy"]
    assert "API Error" in result["dxy"]["error"]


@pytest.mark.asyncio
async def test_collector_cache_hit(mock_cache, mock_provider):
    """Test collectors skip provider calls when cache hits."""
    collector = DXYCollector(cache=mock_cache)
    collector.get_provider = lambda name: mock_provider
    
    mock_cache.get.return_value = {"trend": "BEARISH", "cached": True}
    
    result = await collector.collect("USD")
    
    assert "dxy" in result
    assert result["dxy"]["cached"] is True
    assert mock_provider.get_historical_candles.call_count == 0
