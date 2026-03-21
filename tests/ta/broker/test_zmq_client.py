"""Tests for ZmqClient candle parsing and capabilities."""

from datetime import datetime, timezone

import pytest

from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.mt5.zmq.client import ZmqClient
from engine.ta.constants import Timeframe
from engine.ta.models.candle import Candle


@pytest.fixture
def zmq_config():
    return MT5Config(
        provider="native",
        zmq_host="127.0.0.1",
        zmq_port=5555,
    )


@pytest.fixture
def client(zmq_config):
    return ZmqClient(config=zmq_config)


class TestZmqCandleParsing:
    """Test _parse_candles converts ZMQ EA JSON to Candle models."""

    def test_parse_unix_timestamp(self):
        raw = [
            {
                "time": 1705312800,
                "open": 1.09500,
                "high": 1.09600,
                "low": 1.09400,
                "close": 1.09550,
                "tick_volume": 1234,
            }
        ]

        candles = ZmqClient._parse_candles(raw, "EURUSD", Timeframe.H1)

        assert len(candles) == 1
        c = candles[0]
        assert isinstance(c, Candle)
        assert c.symbol == "EURUSD"
        assert c.timeframe == Timeframe.H1
        assert c.open == 1.09500
        assert c.high == 1.09600
        assert c.low == 1.09400
        assert c.close == 1.09550
        assert c.volume == 1234.0
        assert c.timestamp.tzinfo is not None

    def test_parse_iso_string_timestamp(self):
        raw = [
            {
                "time": "2024-01-15T10:00:00.000Z",
                "open": 1.09,
                "high": 1.10,
                "low": 1.08,
                "close": 1.095,
                "tick_volume": 500,
            }
        ]

        candles = ZmqClient._parse_candles(raw, "XAUUSD", Timeframe.D1)

        assert len(candles) == 1
        assert candles[0].symbol == "XAUUSD"
        assert candles[0].timeframe == Timeframe.D1

    def test_parse_multiple_candles(self):
        raw = [
            {"time": 1705312800, "open": 1.09, "high": 1.10, "low": 1.08, "close": 1.095, "tick_volume": 100},
            {"time": 1705316400, "open": 1.095, "high": 1.11, "low": 1.09, "close": 1.10, "tick_volume": 200},
        ]

        candles = ZmqClient._parse_candles(raw, "USDJPY", Timeframe.M5)

        assert len(candles) == 2
        assert candles[0].timestamp < candles[1].timestamp

    def test_parse_skips_missing_time(self):
        raw = [
            {"open": 1.09, "high": 1.10, "low": 1.08, "close": 1.095, "tick_volume": 100},
            {"time": None, "open": 1.09, "high": 1.10, "low": 1.08, "close": 1.095, "tick_volume": 100},
        ]

        candles = ZmqClient._parse_candles(raw, "EURUSD", Timeframe.H1)
        assert len(candles) == 0

    def test_parse_zero_volume_defaults(self):
        raw = [
            {"time": 1705312800, "open": 1.09, "high": 1.10, "low": 1.08, "close": 1.095},
        ]

        candles = ZmqClient._parse_candles(raw, "EURUSD", Timeframe.H4)
        assert candles[0].volume == 0.0


class TestZmqClientInit:
    """Test ZmqClient initialization."""

    def test_endpoint_construction(self, client):
        assert client._endpoint == "tcp://127.0.0.1:5555"
        assert client._initialized is False

    def test_broker_id(self, client):
        assert client.broker_id == "mt5"


class TestZmqCapabilities:
    """Test get_capabilities returns correct values."""

    @pytest.mark.asyncio
    async def test_capabilities(self, client):
        caps = await client.get_capabilities()

        assert caps.supports_realtime is True
        assert caps.supports_historical is True
        assert caps.supports_symbol_info is True
        assert caps.requires_authentication is True
        assert caps.max_candles_per_request == 5000
        assert caps.rate_limit_per_minute == 1000
