"""Tests for the MT5 broker factory."""

from unittest.mock import MagicMock

import pytest

from engine.shared.exceptions import ConfigurationError
from engine.ta.broker.base import BrokerBase
from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.mt5.factory import create_mt5_broker
from engine.ta.broker.mt5.metaapi.client import MetaApiClient
from engine.ta.broker.mt5.zmq.client import ZmqClient


class TestCreateMT5Broker:
    """Test factory returns the correct client type."""

    def test_metaapi_provider_returns_metaapi_client(self):
        config = MT5Config(
            provider="metaapi",
            metaapi_token="tok-123",
            metaapi_account_id="acc-456",
        )
        http_client = MagicMock()

        client = create_mt5_broker(config=config, http_client=http_client)

        assert isinstance(client, MetaApiClient)
        assert isinstance(client, BrokerBase)
        assert client.broker_id == "mt5"

    def test_native_provider_returns_zmq_client(self):
        config = MT5Config(
            provider="native",
            zmq_host="127.0.0.1",
            zmq_port=5555,
        )

        client = create_mt5_broker(config=config, http_client=None)

        assert isinstance(client, ZmqClient)
        assert isinstance(client, BrokerBase)
        assert client.broker_id == "mt5"

    def test_metaapi_provider_requires_http_client(self):
        config = MT5Config(
            provider="metaapi",
            metaapi_token="tok",
            metaapi_account_id="acc",
        )

        with pytest.raises(ConfigurationError, match="HttpClient is required"):
            create_mt5_broker(config=config, http_client=None)

    def test_native_provider_does_not_require_http_client(self):
        config = MT5Config(
            provider="native",
        )

        client = create_mt5_broker(config=config, http_client=None)
        assert isinstance(client, ZmqClient)
