"""Tests for MetaApiClient candle parsing and capabilities."""

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
            {
                "time": "2024-01-15T10:00:00.000Z",
                "open": 1.09,
                "high": 1.10,
                "low": 1.08,
                "close": 1.095,
                "tickVolume": 100,
            },
            {
                "time": "2024-01-15T11:00:00.000Z",
                "open": 1.095,
                "high": 1.11,
                "low": 1.09,
                "close": 1.10,
                "tickVolume": 200,
            },
            {
                "time": "2024-01-15T12:00:00.000Z",
                "open": 1.10,
                "high": 1.12,
                "low": 1.09,
                "close": 1.11,
                "tickVolume": 300,
            },
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
    async def test_place_order_injects_client_id(self, client):
        """Test that place_order includes clientId when comment is provided."""
        mock_post = AsyncMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"orderId": "123", "stringCode": "TRADE_RETCODE_DONE"})
        mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_post.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_api_post", new_callable=AsyncMock) as mock_api_post:
            mock_api_post.return_value = {"orderId": "123", "stringCode": "TRADE_RETCODE_DONE"}

            await client.place_order(
                symbol="EURUSD",
                direction="BUY",
                order_type="MARKET",
                price=1.10,
                stop_loss=1.09,
                take_profit=1.12,
                lot_size=1.0,
                comment="TEST-ANALYSIS-123",
            )

            mock_api_post.assert_called_once()
            _, kwargs = mock_api_post.call_args
            kwargs.get("payload", args[0] if (args := mock_api_post.call_args.args) else {})
            # The second positional arg to _api_post is the payload dict
            call_args = mock_api_post.call_args
            actual_payload = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("payload", {})
            assert actual_payload.get("clientId") == "TEST-ANALYSIS-123"

    @pytest.mark.asyncio
    async def test_place_order_no_comment_omits_client_id(self, client):
        """Test that place_order omits clientId when no comment is provided."""
        with patch.object(client, "_api_post", new_callable=AsyncMock) as mock_api_post:
            mock_api_post.return_value = {"orderId": "123", "stringCode": "TRADE_RETCODE_DONE"}

            await client.place_order(
                symbol="EURUSD",
                direction="BUY",
                order_type="MARKET",
                price=1.10,
                stop_loss=1.09,
                take_profit=1.12,
                lot_size=1.0,
            )

            call_args = mock_api_post.call_args
            actual_payload = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("payload", {})
            assert "clientId" not in actual_payload
