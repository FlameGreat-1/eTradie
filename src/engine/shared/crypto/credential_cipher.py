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
Data layer (DEK encrypting the credential): **AES-256-GCM** -- a
256-bit DEK, a 96-bit random nonce, and the GCM authentication tag
(AEAD). This satisfies the "AES-256 encryption at rest" requirement
with an authenticated cipher.

Wrap layer (KEK encrypting the DEK): **Fernet** (AES-128-CBC +
HMAC-SHA256). The KEK only ever protects the 32-byte DEK, so the wrap
strength is not the data-at-rest strength; retaining Fernet here means
the KEK derivation, the env wiring, and -- critically -- decryption of
every pre-existing ciphertext are all unchanged.

Ciphertext formats (self-describing, versioned by scheme tag)
-------------------------------------------------------------
Active (v2, AES-256-GCM data layer)::

    v2:<key_version>:<b64(wrapped_dek)>:<b64(nonce)>:<b64(gcm_ct||tag)>

Legacy (pre-envelope, no scheme prefix -- still decrypted): a bare
Fernet token produced by the previous implementation via
``Fernet(KEK).encrypt(plaintext)``.

``decrypt`` transparently handles BOTH on-disk formats, so existing
broker + LLM rows keep working unchanged. ``encrypt`` always writes the
active scheme (v2). The re-wrap maintenance job upgrades legacy rows to
v2 and re-wraps any v2 row whose KEK version is no longer active.

There is intentionally no ``v1`` scheme: the only formats this engine
has ever persisted are the active v2 envelope and the pre-envelope
legacy bare-Fernet token. Adding an unreachable scheme branch would be
dead code, so the format set is deliberately the two that exist.

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

from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from engine.shared.exceptions import ConfigurationError, ETradieBaseError
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Self-describing ciphertext scheme tag.
#   v2 = AES-256-GCM data layer (active write scheme).
# Legacy (no prefix) = bare Fernet token (still decrypted; upgraded to
#   v2 on re-wrap). These are the only two formats this engine has ever
#   written, so there is intentionally no v1 scheme.
_SCHEME_V2 = "v2"
_ACTIVE_SCHEME = _SCHEME_V2
_FIELD_SEP = ":"
_V2_FIELD_COUNT = 5  # v2:<ver>:<wrapped_dek>:<nonce>:<ct||tag>

# AES-256-GCM parameters. 32-byte key = AES-256; 12-byte (96-bit) nonce
# is the GCM standard and is generated fresh per encrypt call. The DEK
# key size is sourced from _AES256_KEY_BYTES so there is one source of
# truth for "this is AES-256".
_AES256_KEY_BYTES = 32
_GCM_NONCE_BYTES = 12

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
        self._keks: dict[int, Fernet] = {ver: Fernet(key) for ver, key in keks_by_version.items()}
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
        """Envelope-encrypt ``plaintext`` and return a ``v2`` token.

        A fresh DEK is generated per call (256-bit, sized from
        ``_AES256_KEY_BYTES``) and used to encrypt the plaintext with
        AES-256-GCM (fresh 96-bit nonce, AEAD tag). The DEK is then
        wrapped with the active KEK (Fernet wrap). The GCM ciphertext
        returned by ``AESGCM.encrypt`` already has the 16-byte
        authentication tag appended.
        """
        dek = AESGCM.generate_key(bit_length=_AES256_KEY_BYTES * 8)
        nonce = os.urandom(_GCM_NONCE_BYTES)
        ciphertext = AESGCM(dek).encrypt(nonce, plaintext.encode(), None)
        wrapped_dek = self._keks[self._active_version].encrypt(dek)
        return _FIELD_SEP.join(
            (
                _SCHEME_V2,
                str(self._active_version),
                base64.urlsafe_b64encode(wrapped_dek).decode(),
                base64.urlsafe_b64encode(nonce).decode(),
                base64.urlsafe_b64encode(ciphertext).decode(),
            )
        )

    # -- Decrypt -----------------------------------------------------------

    def decrypt(self, token: str) -> str:
        """Decrypt a credential token (v2 AES-256-GCM, or legacy Fernet)."""
        if token.startswith(_SCHEME_V2 + _FIELD_SEP):
            return self._decrypt_v2(token)
        return self._decrypt_legacy(token)

    def _unwrap_dek(self, version: int, wrapped_dek_b64: str) -> bytes:
        """Resolve the KEK for ``version`` and unwrap the DEK.

        Raises CredentialDecryptionError when the version is not
        configured (e.g. the key was revoked before the row was
        re-wrapped).
        """
        kek = self._keks.get(version)
        if kek is None:
            raise CredentialDecryptionError(
                "Credential was wrapped with an unconfigured KEK version",
                details={"key_version": version, "configured": sorted(self._keks)},
            )
        wrapped_dek = base64.urlsafe_b64decode(wrapped_dek_b64.encode())
        return kek.decrypt(wrapped_dek)

    def _decrypt_v2(self, token: str) -> str:
        parts = token.split(_FIELD_SEP, _V2_FIELD_COUNT - 1)
        if len(parts) != _V2_FIELD_COUNT:
            raise CredentialDecryptionError(
                "Malformed v2 credential token",
                details={"reason": "expected 5 colon-separated fields"},
            )
        _, version_str, wrapped_dek_b64, nonce_b64, ciphertext_b64 = parts
        try:
            version = int(version_str)
        except ValueError as exc:
            raise CredentialDecryptionError(
                "Malformed v2 credential token",
                details={"reason": "non-integer key version"},
            ) from exc
        try:
            dek = self._unwrap_dek(version, wrapped_dek_b64)
            nonce = base64.urlsafe_b64decode(nonce_b64.encode())
            ciphertext = base64.urlsafe_b64decode(ciphertext_b64.encode())
            return AESGCM(dek).decrypt(nonce, ciphertext, None).decode()
        except CredentialDecryptionError:
            raise
        except (InvalidToken, InvalidTag, ValueError, TypeError) as exc:
            raise CredentialDecryptionError(
                "Failed to decrypt v2 credential token",
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
        """True when ``token`` is not on the active scheme + active KEK.

        Returns True for: legacy (no scheme -> upgrade to v2
        AES-256-GCM) and any v2 token wrapped under a non-active KEK
        version. Used by the maintenance routine to find rows worth
        re-wrapping after a key rotation or a scheme upgrade.
        """
        # Legacy (no scheme prefix) needs upgrading to the active scheme.
        if not token.startswith(_ACTIVE_SCHEME + _FIELD_SEP):
            return True
        # Active scheme: re-wrap only when the KEK version is not active.
        version = self.key_version_of(token)
        if version is None:
            return False  # malformed; leave it for decrypt() to surface
        return version != self._active_version

    def key_version_of(self, token: str) -> int | None:
        """Return the KEK version a v2 token is wrapped under, else None.

        None for legacy (no versioned wrap) or malformed tokens. Used by
        the repositories to stamp an accurate ``key_version`` derived
        from the ciphertext actually stored, rather than assuming the
        active version, and by ``needs_rewrap`` to decide if a v2 row is
        already on the active KEK.
        """
        if not token.startswith(_ACTIVE_SCHEME + _FIELD_SEP):
            return None
        parts = token.split(_FIELD_SEP, _V2_FIELD_COUNT - 1)
        if len(parts) != _V2_FIELD_COUNT:
            return None
        try:
            return int(parts[1])
        except ValueError:
            return None

    def rewrap(self, token: str) -> str:
        """Return an equivalent active-scheme token (v2) under the active KEK.

        Decrypts to plaintext using whichever scheme/version applies
        (v2 or legacy), then re-encrypts via ``encrypt`` -- which always
        emits the active scheme (v2, AES-256-GCM) wrapped by the active
        KEK. The stored credential value is unchanged; only its
        protection is upgraded. This is what migrates legacy rows to
        AES-256 and what completes a KEK rotation.
        """
        plaintext = self.decrypt(token)
        return self.encrypt(plaintext)


# ---------------------------------------------------------------------------
# Environment-backed process singleton
# ---------------------------------------------------------------------------

_singleton_lock = threading.Lock()
_singleton: CredentialCipher | None = None


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
        suffix = env_name[len(_VERSIONED_KEY_PREFIX) :]
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
    """Envelope-encrypt a credential with the active KEK version (v2)."""
    return get_cipher().encrypt(plaintext)


def decrypt_credential(token: str) -> str:
    """Decrypt a credential token (v2 AES-256-GCM envelope, or legacy Fernet)."""
    return get_cipher().decrypt(token)


def active_key_version() -> int:
    """Current active KEK version (persisted alongside new ciphertext)."""
    return get_cipher().active_version


def key_version_of(token: str) -> int | None:
    """KEK version a v2 token is wrapped under, or None (legacy/malformed)."""
    return get_cipher().key_version_of(token)


def needs_rewrap(token: str) -> bool:
    """True when ``token`` should be re-wrapped to the active KEK version."""
    return get_cipher().needs_rewrap(token)


def rewrap_credential(token: str) -> str:
    """Re-wrap ``token`` to the active KEK version (rotation maintenance)."""
    return get_cipher().rewrap(token)
