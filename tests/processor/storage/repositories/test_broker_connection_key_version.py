"""Tests for BrokerConnectionRepository._effective_key_version.

broker_connections has two encrypted columns but a single key_version
column. The helper must report the truthful "is this row fully on the
active KEK?" value (audit item 5):

  - None when no secret is stored,
  - None when ANY non-null column is legacy / non-v2,
  - otherwise the minimum KEK version across non-null columns.
"""

from __future__ import annotations

import base64
import hashlib

import pytest
from cryptography.fernet import Fernet

from engine.processor.storage.repositories.broker_connection_repository import (
    BrokerConnectionRepository,
)
from engine.shared.crypto import active_key_version, encrypt_credential
from engine.shared.crypto.credential_cipher import reset_cipher_for_tests

_KEY_V1 = "broker-keyver-test-kek"


@pytest.fixture
def single_kek(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("BROKER_ENCRYPTION_KEY", _KEY_V1)
    monkeypatch.delenv("BROKER_ENCRYPTION_KEY_V2", raising=False)
    reset_cipher_for_tests()
    yield
    reset_cipher_for_tests()


def _legacy_token(raw_kek: str, plaintext: str) -> str:
    digest = hashlib.sha256(raw_kek.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest)).encrypt(plaintext.encode()).decode()


_fn = BrokerConnectionRepository._effective_key_version


class TestEffectiveKeyVersion:
    def test_no_secrets_is_none(self, single_kek):
        assert _fn(None, None) is None

    def test_all_active_returns_active(self, single_kek):
        a = encrypt_credential("pw")
        b = encrypt_credential("ea")
        assert _fn(a, b) == active_key_version()

    def test_single_active_column_returns_active(self, single_kek):
        assert _fn(encrypt_credential("pw"), None) == active_key_version()

    def test_any_legacy_column_forces_none(self, single_kek):
        active_token = encrypt_credential("pw")
        legacy = _legacy_token(_KEY_V1, "ea")
        assert _fn(active_token, legacy) is None
        assert _fn(legacy, active_token) is None

    def test_mixed_versions_returns_min(self, single_kek):
        # A v2 token explicitly under version 1, paired with an active
        # (also version 1 here) token -> min is 1.
        active_token = encrypt_credential("pw")  # version 1
        # Craft a v2 token claiming version 5 to exercise the min logic
        # without needing a second configured KEK; only the version
        # field is read by key_version_of.
        _, _ver, wrapped, nonce, ct = active_token.split(":", 4)
        token_v5 = ":".join(("v2", "5", wrapped, nonce, ct))
        assert _fn(active_token, token_v5) == 1
        assert _fn(token_v5, token_v5) == 5
