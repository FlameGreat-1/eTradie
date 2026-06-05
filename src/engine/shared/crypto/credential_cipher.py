"""Versioned envelope encryption for credentials at rest.

This module is the single source of truth for credential-at-rest
cryptography in the engine. It is consumed by both the broker- and
LLM-connection repositories.

Why envelope encryption
-----------------------
A flat "encrypt every secret directly with one key" scheme cannot be
rotated without re-encrypting every ciphertext, has no key-encryption
key (KEK), and offers no per-record key separation. The industry
standard (AWS KMS, GCP KMS, HashiCorp Vault Transit) is *envelope
encryption*:

  1. Generate a fresh random Data Encryption Key (DEK) per record.
  2. Encrypt the plaintext with the DEK.
  3. Encrypt ("wrap") the DEK with a Key Encryption Key (KEK).
  4. Store {wrapped_dek, ciphertext, kek_version} together.

Rotating the KEK only requires re-wrapping the (tiny) DEKs, never
re-encrypting the (arbitrary-size) plaintext. Revoking a KEK version
is removing it from the configured set.

Cipher choice
-------------
The data layer and the wrap layer both use Fernet
(AES-128-CBC + HMAC-SHA256), the authenticated-encryption primitive the
rest of the platform already standardised on. Fernet is retained
deliberately (see ``docs/security/TIER3_CREDENTIAL_ENCRYPTION.md``):
it is NIST-strength and authenticated, and keeping it lets every
pre-existing ciphertext decrypt with zero migration.

Ciphertext format
-----------------
New ciphertext is self-describing and versioned::

    v1:<key_version>:<urlsafe_b64(wrapped_dek)>:<fernet(dek, plaintext)>

Legacy ciphertext (written before this module existed) has NO ``v1:``
prefix and is a bare Fernet token produced by
``Fernet(KEK).encrypt(plaintext)``. ``decrypt`` transparently handles
both, so existing broker + LLM rows keep working unchanged.

KEK versioning
--------------
KEK material comes from the environment, sourced from Vault via the
engine ExternalSecret:

  - ``BROKER_ENCRYPTION_KEY``           -> version 1 (the base key).
  - ``BROKER_ENCRYPTION_KEY_V<n>``      -> version <n> (n >= 2).

The highest configured version is the *active* write key. All
configured versions are tried (active first) when decrypting legacy
tokens or unwrapping a DEK, so rotation is non-breaking. Removing a
version from the environment revokes it.

Each raw KEK value is normalised to a Fernet key exactly as the legacy
repositories did it: ``urlsafe_b64encode(sha256(raw))``. This is what
guarantees a given env value yields the identical Fernet key as before,
so legacy ciphertext produced by the old code decrypts here verbatim.
"""
from __future__ import annotations

import base64
import hashlib
import os
import threading
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from engine.shared.exceptions import ConfigurationError, ETradieBaseError
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Current self-describing ciphertext scheme tag.
_SCHEME_V1 = "v1"
_FIELD_SEP = ":"

# Base KEK env var (version 1) and the versioned-override prefix.
_BASE_KEY_ENV = "BROKER_ENCRYPTION_KEY"
_VERSIONED_KEY_PREFIX = "BROKER_ENCRYPTION_KEY_V"
_BASE_KEY_VERSION = 1

# Dev-only fallback. Matches the broker repository's historical dev
# posture (a single, clearly-labelled literal). Production / staging
# never reach this branch -- they fail fast instead.
_DEV_FALLBACK_RAW = "etradie-dev-only-broker-key-do-not-use-in-production"


class CredentialDecryptionError(ETradieBaseError):
    """Raised when a credential ciphertext cannot be decrypted with any
    configured KEK version (malformed token, or the key that produced
    it is no longer configured)."""


def _normalise_kek(raw: str) -> bytes:
    """Derive a Fernet key from a raw KEK string.

    ``urlsafe_b64encode(sha256(raw))`` -- identical to the legacy
    repositories so a given raw value yields the SAME Fernet key,
    which is what lets legacy ciphertext decrypt unchanged.
    """
    digest = hashlib.sha256(raw.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _is_prod_like() -> bool:
    return os.environ.get("APP_ENV", "development").strip().lower() in (
        "production",
        "staging",
    )


class CredentialCipher:
    """Envelope cipher with a versioned KEK set.

    Construct once and reuse; the instance caches the resolved KEK
    Fernet objects. Use the module-level ``encrypt_credential`` /
    ``decrypt_credential`` helpers for the common case -- they share a
    process-wide singleton built from the environment.
    """

    def __init__(self, keks_by_version: dict[int, bytes]) -> None:
        if not keks_by_version:
            raise ConfigurationError(
                "CredentialCipher requires at least one KEK version",
            )
        self._keks: dict[int, Fernet] = {
            ver: Fernet(key) for ver, key in keks_by_version.items()
        }
        # Active = highest configured version (the write key).
        self._active_version: int = max(self._keks)
        # Decryption trial order: active first, then the rest descending,
        # so the common (current-key) case unwraps on the first try.
        self._trial_order: list[int] = sorted(self._keks, reverse=True)

    # -- Properties --------------------------------------------------------

    @property
    def active_version(self) -> int:
        """The KEK version new ciphertext is wrapped under."""
        return self._active_version

    # -- Encrypt -----------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """Envelope-encrypt ``plaintext`` and return a ``v1`` token.

        A fresh DEK is generated per call, used to encrypt the
        plaintext, then wrapped with the active KEK.
        """
        dek = Fernet.generate_key()
        ciphertext = Fernet(dek).encrypt(plaintext.encode())
        wrapped_dek = self._keks[self._active_version].encrypt(dek)
        return _FIELD_SEP.join(
            (
                _SCHEME_V1,
                str(self._active_version),
                base64.urlsafe_b64encode(wrapped_dek).decode(),
                ciphertext.decode(),
            )
        )

    # -- Decrypt -----------------------------------------------------------

    def decrypt(self, token: str) -> str:
        """Decrypt a credential token (``v1`` envelope OR legacy Fernet)."""
        if token.startswith(_SCHEME_V1 + _FIELD_SEP):
            return self._decrypt_v1(token)
        return self._decrypt_legacy(token)

    def _decrypt_v1(self, token: str) -> str:
        parts = token.split(_FIELD_SEP, 3)
        if len(parts) != 4:
            raise CredentialDecryptionError(
                "Malformed v1 credential token",
                details={"reason": "expected 4 colon-separated fields"},
            )
        _, version_str, wrapped_dek_b64, ciphertext = parts
        try:
            version = int(version_str)
        except ValueError as exc:
            raise CredentialDecryptionError(
                "Malformed v1 credential token",
                details={"reason": "non-integer key version"},
            ) from exc

        kek = self._keks.get(version)
        if kek is None:
            raise CredentialDecryptionError(
                "Credential was wrapped with an unconfigured KEK version",
                details={"key_version": version, "configured": sorted(self._keks)},
            )
        try:
            wrapped_dek = base64.urlsafe_b64decode(wrapped_dek_b64.encode())
            dek = kek.decrypt(wrapped_dek)
            return Fernet(dek).decrypt(ciphertext.encode()).decode()
        except (InvalidToken, ValueError, TypeError) as exc:
            raise CredentialDecryptionError(
                "Failed to decrypt v1 credential token",
                details={"key_version": version},
            ) from exc

    def _decrypt_legacy(self, token: str) -> str:
        """Decrypt a pre-envelope bare Fernet token.

        Tries every configured KEK (active first). Legacy tokens were
        produced by ``Fernet(KEK).encrypt(...)`` directly, so the KEK
        itself is the decryption key here (no DEK).
        """
        raw = token.encode()
        for version in self._trial_order:
            try:
                return self._keks[version].decrypt(raw).decode()
            except InvalidToken:
                continue
        raise CredentialDecryptionError(
            "Failed to decrypt legacy credential token with any configured KEK",
            details={"configured": sorted(self._keks)},
        )

    # -- Rotation / rewrap -------------------------------------------------

    def needs_rewrap(self, token: str) -> bool:
        """True when ``token`` is legacy OR wrapped under a non-active KEK.

        Used by the maintenance routine to find rows worth re-wrapping
        after a key rotation.
        """
        if not token.startswith(_SCHEME_V1 + _FIELD_SEP):
            return True
        parts = token.split(_FIELD_SEP, 3)
        if len(parts) != 4:
            return False  # malformed; leave it for decrypt() to surface
        try:
            return int(parts[1]) != self._active_version
        except ValueError:
            return False

    def rewrap(self, token: str) -> str:
        """Return an equivalent ``v1`` token wrapped under the active KEK.

        Decrypts to plaintext using whichever key/version applies, then
        re-encrypts with a fresh DEK wrapped by the active KEK. The
        stored credential value is unchanged; only its protection is
        upgraded. Idempotent: a token already on the active version is
        returned via a clean re-encrypt (still valid, still active).
        """
        plaintext = self.decrypt(token)
        return self.encrypt(plaintext)


# ---------------------------------------------------------------------------
# Environment-backed process singleton
# ---------------------------------------------------------------------------

_singleton_lock = threading.Lock()
_singleton: Optional[CredentialCipher] = None


def _resolve_keks_from_env() -> dict[int, bytes]:
    """Build the versioned KEK map from the environment.

    Version 1 comes from BROKER_ENCRYPTION_KEY; versions >= 2 from
    BROKER_ENCRYPTION_KEY_V<n>. In prod/staging a missing base key is a
    hard ConfigurationError; in dev a single loud-warning fallback is
    used so docker-compose / pytest boot without secrets management.
    """
    keks: dict[int, bytes] = {}

    base = os.environ.get(_BASE_KEY_ENV, "").strip()
    if base:
        keks[_BASE_KEY_VERSION] = _normalise_kek(base)

    # Versioned overrides: BROKER_ENCRYPTION_KEY_V2, _V3, ...
    for env_name, env_val in os.environ.items():
        if not env_name.startswith(_VERSIONED_KEY_PREFIX):
            continue
        suffix = env_name[len(_VERSIONED_KEY_PREFIX):]
        if not suffix.isdigit():
            continue
        version = int(suffix)
        val = env_val.strip()
        if not val:
            continue
        keks[version] = _normalise_kek(val)

    if not keks:
        if _is_prod_like():
            raise ConfigurationError(
                "BROKER_ENCRYPTION_KEY is required in production/staging. "
                "Set it via the engine ExternalSecret (Vault path "
                "etradie/services/engine/<env>:broker_encryption_key).",
                details={"env_var": _BASE_KEY_ENV},
            )
        logger.warning(
            "credential_encryption_key_missing_using_dev_fallback",
            extra={
                "warning": (
                    "BROKER_ENCRYPTION_KEY is not set. Using the dev-only "
                    "fallback. DO NOT use this in production or staging."
                ),
            },
        )
        keks[_BASE_KEY_VERSION] = _normalise_kek(_DEV_FALLBACK_RAW)

    return keks


def get_cipher() -> CredentialCipher:
    """Return the process-wide cipher, building it on first use.

    The KEK set is read once from the environment. A deployment rotates
    keys by restarting pods with the new BROKER_ENCRYPTION_KEY_V<n>
    present, which is the same operational model as every other engine
    secret delivered by the ExternalSecret.
    """
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = CredentialCipher(_resolve_keks_from_env())
    return _singleton


def reset_cipher_for_tests() -> None:
    """Drop the cached singleton so a test can re-read the environment.

    Test-only seam; production never calls this.
    """
    global _singleton
    with _singleton_lock:
        _singleton = None


# ---------------------------------------------------------------------------
# Module-level convenience API (what the repositories import)
# ---------------------------------------------------------------------------


def encrypt_credential(plaintext: str) -> str:
    """Envelope-encrypt a credential with the active KEK version."""
    return get_cipher().encrypt(plaintext)


def decrypt_credential(token: str) -> str:
    """Decrypt a credential token (v1 envelope or legacy Fernet)."""
    return get_cipher().decrypt(token)


def active_key_version() -> int:
    """Current active KEK version (persisted alongside new ciphertext)."""
    return get_cipher().active_version


def needs_rewrap(token: str) -> bool:
    """True when ``token`` should be re-wrapped to the active KEK version."""
    return get_cipher().needs_rewrap(token)


def rewrap_credential(token: str) -> str:
    """Re-wrap ``token`` to the active KEK version (rotation maintenance)."""
    return get_cipher().rewrap(token)
