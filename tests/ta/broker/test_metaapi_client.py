"""Tests for MetaApiClient candle parsing and capabilities."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.mt5.metaapi.client import MetaApiClient
from engine.ta.constants import Timeframe
from engine.ta.models.candle import Candle


@pytest.fixture
def metaapi_config():
    return MT5Config(
        provider="metaapi",
        metaapi_token="test-token",
        metaapi_account_id="test-account",
    )


@pytest.fixture
def mock_http():
    return MagicMock()


@pytest.fixture
def client(metaapi_config, mock_http):
    return MetaApiClient(config=metaapi_config, http_client=mock_http)


class TestMetaApiCandleParsing:
    """Test _parse_candles converts MetaApi JSON to Candle models."""

    def test_parse_standard_candle(self):
        raw = [
            {
                "time": "2024-01-15T10:00:00.000Z",
                "brokerTime": "2024-01-15 12:00:00.000",
                "open": 1.09500,
                "high": 1.09600,
                "low": 1.09400,
                "close": 1.09550,
                "tickVolume": 1234,
            }
        ]

        candles = MetaApiClient._parse_candles(raw, "EURUSD", Timeframe.H1)

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

    def test_parse_multiple_candles(self):
        raw = [
            {"time": "2024-01-15T10:00:00.000Z", "open": 1.09, "high": 1.10, "low": 1.08, "close": 1.095, "tickVolume": 100},
            {"time": "2024-01-15T11:00:00.000Z", "open": 1.095, "high": 1.11, "low": 1.09, "close": 1.10, "tickVolume": 200},
            {"time": "2024-01-15T12:00:00.000Z", "open": 1.10, "high": 1.12, "low": 1.09, "close": 1.11, "tickVolume": 300},
        ]

        candles = MetaApiClient._parse_candles(raw, "GBPUSD", Timeframe.M15)

        assert len(candles) == 3
        assert candles[0].timestamp < candles[1].timestamp < candles[2].timestamp
        assert all(c.symbol == "GBPUSD" for c in candles)
        assert all(c.timeframe == Timeframe.M15 for c in candles)

    def test_parse_skips_missing_time(self):
        raw = [
            {"open": 1.09, "high": 1.10, "low": 1.08, "close": 1.095},
            {"time": "", "open": 1.09, "high": 1.10, "low": 1.08, "close": 1.095},
        ]

        candles = MetaApiClient._parse_candles(raw, "EURUSD", Timeframe.H1)
        assert len(candles) == 0

    def test_parse_zero_volume_defaults(self):
        raw = [
            {"time": "2024-01-15T10:00:00.000Z", "open": 1.09, "high": 1.10, "low": 1.08, "close": 1.095},
        ]

        candles = MetaApiClient._parse_candles(raw, "EURUSD", Timeframe.H1)
        assert candles[0].volume == 0.0


class TestMetaApiCapabilities:
    """Test get_capabilities returns correct values."""

    @pytest.mark.asyncio
    async def test_capabilities(self, client):
        caps = await client.get_capabilities()

        assert caps.supports_realtime is True
        assert caps.supports_historical is True
        assert caps.supports_symbol_info is True
        assert caps.requires_authentication is True
        assert caps.max_candles_per_request == 5000

class TestMetaApiExecutionIdempotency:
    """Test idempotency key (clientId) injection on execution endpoints."""

    @pytest.mark.asyncio
    @patch("engine.ta.broker.mt5.metaapi.client.aiohttp.ClientSession.post")
    async def test_place_order_injects_client_id(self, mock_post, client):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"orderId": "123", "stringCode": "TRADE_RETCODE_DONE"})
        mock_post.return_value.__aenter__.return_value = mock_resp

        # Call with an analysis ID (comment)
        from engine.ta.broker.base import OrderType
        
        await client.place_order(
            symbol="EURUSD",
            order_type=OrderType.BUY,
            volume=1.0,
            price=1.10,
            comment="TEST-ANALYSIS-123"
        )
        
        # Verify post was called
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        
        # Verify the json payload contains clientId matching the comment
        payload = kwargs.get("json", {})
        assert "clientId" in payload
        assert payload["clientId"] == "TEST-ANALYSIS-123"

    @pytest.mark.asyncio
    @patch("engine.ta.broker.mt5.metaapi.client.aiohttp.ClientSession.post")
    async def test_place_order_no_comment_omits_client_id(self, mock_post, client):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"orderId": "123", "stringCode": "TRADE_RETCODE_DONE"})
        mock_post.return_value.__aenter__.return_value = mock_resp

        from engine.ta.broker.base import OrderType
        
        # Call WITHOUT an analysis ID (comment)
        await client.place_order(
            symbol="EURUSD",
            order_type=OrderType.BUY,
            volume=1.0,
            price=1.10
        )
        
        # Verify post was called
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        
        # Verify clientId is NOT present
        payload = kwargs.get("json", {})
        assert "clientId" not in payload
