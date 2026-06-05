"""Tests for the shared credential envelope cipher.

Covers the two on-disk ciphertext formats (active v2 AES-256-GCM and
legacy bare-Fernet), KEK versioning / rotation, the rewrap primitives,
and the key_version_of helper used by the repositories.

Each test rebuilds the process-wide cipher singleton from a known
environment via reset_cipher_for_tests() so KEK configuration is
deterministic and isolated.
"""

from __future__ import annotations

import base64
import hashlib

import pytest
from cryptography.fernet import Fernet

from engine.shared.crypto import (
    CredentialDecryptionError,
    active_key_version,
    decrypt_credential,
    encrypt_credential,
    key_version_of,
    needs_rewrap,
    rewrap_credential,
)
from engine.shared.crypto.credential_cipher import reset_cipher_for_tests

_KEY_V1 = "unit-test-kek-version-one"
_KEY_V2 = "unit-test-kek-version-two"
_PLAINTEXT = "s3cr3t-broker-password!"


def _legacy_fernet_token(raw_kek: str, plaintext: str) -> str:
    """Reproduce a pre-envelope bare-Fernet token exactly as the previous
    repository implementation produced it: Fernet key =
    urlsafe_b64encode(sha256(raw)), then Fernet(key).encrypt(plaintext).
    """
    digest = hashlib.sha256(raw_kek.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key).encrypt(plaintext.encode()).decode()


@pytest.fixture
def single_kek(monkeypatch):
    """Configure exactly one KEK version (the base key) and reset the
    cipher so it reads this environment."""
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("BROKER_ENCRYPTION_KEY", _KEY_V1)
    monkeypatch.delenv("BROKER_ENCRYPTION_KEY_V2", raising=False)
    reset_cipher_for_tests()
    yield
    reset_cipher_for_tests()


@pytest.fixture
def rotated_kek(monkeypatch):
    """Configure base KEK (v1) + a higher rotation KEK (v2), so the active
    version is 2."""
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("BROKER_ENCRYPTION_KEY", _KEY_V1)
    monkeypatch.setenv("BROKER_ENCRYPTION_KEY_V2", _KEY_V2)
    reset_cipher_for_tests()
    yield
    reset_cipher_for_tests()


class TestV2RoundTrip:
    def test_encrypt_then_decrypt_returns_plaintext(self, single_kek):
        token = encrypt_credential(_PLAINTEXT)
        assert decrypt_credential(token) == _PLAINTEXT

    def test_token_is_v2_under_active_version(self, single_kek):
        token = encrypt_credential(_PLAINTEXT)
        assert token.startswith("v2:")
        assert key_version_of(token) == active_key_version() == 1

    def test_two_encrypts_use_distinct_nonces(self, single_kek):
        # Fresh DEK + nonce per call -> ciphertext differs even for the
        # same plaintext.
        assert encrypt_credential(_PLAINTEXT) != encrypt_credential(_PLAINTEXT)


class TestLegacyBackCompat:
    def test_legacy_fernet_token_decrypts_unchanged(self, single_kek):
        legacy = _legacy_fernet_token(_KEY_V1, _PLAINTEXT)
        assert decrypt_credential(legacy) == _PLAINTEXT

    def test_legacy_token_has_no_versioned_wrap(self, single_kek):
        legacy = _legacy_fernet_token(_KEY_V1, _PLAINTEXT)
        assert key_version_of(legacy) is None

    def test_legacy_token_needs_rewrap(self, single_kek):
        legacy = _legacy_fernet_token(_KEY_V1, _PLAINTEXT)
        assert needs_rewrap(legacy) is True

    def test_rewrap_upgrades_legacy_to_v2(self, single_kek):
        legacy = _legacy_fernet_token(_KEY_V1, _PLAINTEXT)
        upgraded = rewrap_credential(legacy)
        assert upgraded.startswith("v2:")
        assert decrypt_credential(upgraded) == _PLAINTEXT
        assert needs_rewrap(upgraded) is False


class TestKeyVersionOf:
    def test_active_version_for_v2(self, single_kek):
        assert key_version_of(encrypt_credential(_PLAINTEXT)) == 1

    def test_none_for_legacy(self, single_kek):
        assert key_version_of(_legacy_fernet_token(_KEY_V1, _PLAINTEXT)) is None

    def test_none_for_malformed(self, single_kek):
        assert key_version_of("v2:not-an-int:x:y:z") is None
        assert key_version_of("v2:1:only-three-fields") is None


class TestNeedsRewrap:
    def test_active_v2_does_not_need_rewrap(self, single_kek):
        assert needs_rewrap(encrypt_credential(_PLAINTEXT)) is False

    def test_legacy_needs_rewrap(self, single_kek):
        assert needs_rewrap(_legacy_fernet_token(_KEY_V1, _PLAINTEXT)) is True


class TestNoV1Scheme:
    def test_v1_prefix_is_treated_as_legacy_not_a_special_branch(self, single_kek):
        # The removed v1 path must not leave a trap: a string that merely
        # starts with 'v1:' is not special-cased; it is routed to the
        # legacy bare-Fernet decryptor, which fails cleanly as an
        # undecryptable legacy token (NOT a v1-specific crash).
        with pytest.raises(CredentialDecryptionError):
            decrypt_credential("v1:1:something:else")


class TestRotation:
    def test_active_version_advances_to_highest(self, rotated_kek):
        assert active_key_version() == 2

    def test_new_encrypts_use_active_v2_version(self, rotated_kek):
        token = encrypt_credential(_PLAINTEXT)
        assert key_version_of(token) == 2

    def test_token_under_old_version_needs_rewrap(self, monkeypatch):
        # Write a token while only v1 is configured...
        monkeypatch.setenv("APP_ENV", "testing")
        monkeypatch.setenv("BROKER_ENCRYPTION_KEY", _KEY_V1)
        monkeypatch.delenv("BROKER_ENCRYPTION_KEY_V2", raising=False)
        reset_cipher_for_tests()
        token_v1 = encrypt_credential(_PLAINTEXT)
        assert key_version_of(token_v1) == 1

        # ...then rotate so v2 becomes active.
        monkeypatch.setenv("BROKER_ENCRYPTION_KEY_V2", _KEY_V2)
        reset_cipher_for_tests()
        assert active_key_version() == 2
        assert needs_rewrap(token_v1) is True

        upgraded = rewrap_credential(token_v1)
        assert key_version_of(upgraded) == 2
        assert decrypt_credential(upgraded) == _PLAINTEXT
        assert needs_rewrap(upgraded) is False
        reset_cipher_for_tests()

    def test_revoking_a_version_breaks_its_tokens(self, monkeypatch):
        # Encrypt under v2...
        monkeypatch.setenv("APP_ENV", "testing")
        monkeypatch.setenv("BROKER_ENCRYPTION_KEY", _KEY_V1)
        monkeypatch.setenv("BROKER_ENCRYPTION_KEY_V2", _KEY_V2)
        reset_cipher_for_tests()
        token_v2 = encrypt_credential(_PLAINTEXT)
        assert decrypt_credential(token_v2) == _PLAINTEXT

        # ...revoke v2 (remove it from the environment). The token can no
        # longer be decrypted: its KEK version is unconfigured.
        monkeypatch.delenv("BROKER_ENCRYPTION_KEY_V2", raising=False)
        reset_cipher_for_tests()
        assert active_key_version() == 1
        with pytest.raises(CredentialDecryptionError):
            decrypt_credential(token_v2)
        reset_cipher_for_tests()
