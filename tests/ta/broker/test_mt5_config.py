"""Tests for MT5Config hybrid provider validation."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from engine.ta.broker.mt5.config import MT5Config


class TestMT5ConfigProviderValidation:
    """Test that MT5Config validates credentials per provider."""

    def test_metaapi_provider_requires_token(self):
        with pytest.raises(ValidationError, match="MT5_METAAPI_TOKEN"):
            MT5Config(
                provider="metaapi",
                metaapi_token="",
                metaapi_account_id="acc-123",
            )

    def test_metaapi_provider_requires_account_id(self):
        with pytest.raises(ValidationError, match="MT5_METAAPI_ACCOUNT_ID"):
            MT5Config(
                provider="metaapi",
                metaapi_token="token-abc",
                metaapi_account_id="",
            )

    def test_metaapi_provider_valid(self):
        cfg = MT5Config(
            provider="metaapi",
            metaapi_token="token-abc",
            metaapi_account_id="acc-123",
        )
        assert cfg.provider == "metaapi"
        assert cfg.metaapi_token == "token-abc"
        assert cfg.metaapi_account_id == "acc-123"

    def test_native_provider_valid_without_metaapi_creds(self):
        cfg = MT5Config(
            provider="native",
            zmq_host="192.168.1.50",
            zmq_port=5555,
        )
        assert cfg.provider == "native"
        assert cfg.zmq_host == "192.168.1.50"
        assert cfg.zmq_port == 5555

    def test_native_provider_default_zmq_host(self):
        cfg = MT5Config(provider="native")
        assert cfg.zmq_host == "host.docker.internal"
        assert cfg.zmq_port == 5555

    def test_invalid_provider_rejected(self):
        with pytest.raises(ValidationError):
            MT5Config(provider="invalid")

    def test_default_provider_is_metaapi(self):
        cfg = MT5Config(
            metaapi_token="tok",
            metaapi_account_id="acc",
        )
        assert cfg.provider == "metaapi"

    def test_shared_settings_defaults(self):
        cfg = MT5Config(
            provider="native",
        )
        assert cfg.timeout_seconds == 60
        assert cfg.max_retries == 3
        assert cfg.max_candles_per_request == 5000
        assert cfg.enable_tick_data is False
