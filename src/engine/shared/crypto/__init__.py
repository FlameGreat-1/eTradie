"""Shared credential-at-rest cryptography.

Single source of truth for encrypting user-configured credentials
(broker MT5 passwords / EA tokens, LLM API keys) before they are
persisted. Both the broker-connection and LLM-connection repositories
import from here so there is exactly one cipher, one key-derivation
path, and one ciphertext format across the engine.

See ``credential_cipher`` for the envelope-encryption implementation
and ``docs/security/TIER3_CREDENTIAL_ENCRYPTION.md`` for the design.
"""

from engine.shared.crypto.credential_cipher import (
    CredentialCipher,
    CredentialDecryptionError,
    active_key_version,
    decrypt_credential,
    encrypt_credential,
    key_version_of,
    needs_rewrap,
    rewrap_credential,
)

__all__ = [
    "CredentialCipher",
    "CredentialDecryptionError",
    "active_key_version",
    "decrypt_credential",
    "encrypt_credential",
    "key_version_of",
    "needs_rewrap",
    "rewrap_credential",
]
