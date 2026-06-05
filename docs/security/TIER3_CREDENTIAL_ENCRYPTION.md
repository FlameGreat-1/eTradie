# Tier 3 — Broker Credential Security: implementation tracker

Source of truth for the staged hardening of `CHECKLIST.md` Tier 3.
Updated as each step lands so progress survives across sessions.

## Verified starting state (before this work)

- Broker + LLM credentials encrypted at rest with **Fernet**
  (AES-128-CBC + HMAC-SHA256) in two repositories:
  - `src/engine/processor/storage/repositories/broker_connection_repository.py`
  - `src/engine/processor/storage/repositories/llm_connection_repository.py`
- KEK source: `BROKER_ENCRYPTION_KEY` from Vault via the engine
  ExternalSecret (`helm/engine/templates/externalsecret.yaml`).
- Hosted-MT path stores the MT5 password in Vault KV-v2 per tenant
  with engine=write-only / pod=read-own ACLs
  (`infrastructure/cluster/vault-paths/mt_node_tenant_secrets.tf`).
- `VaultClient` is **KV-v2 only** (no Transit) — `src/engine/shared/vault/client.py`.
- Serializer never exposes the password; logs never include it. (PASS)

## Verified gaps (what this work closes)

| Checklist item | Before | Plan |
| --- | --- | --- |
| AES-256 at rest | Fernet = AES-128 | Keep Fernet (documented decision); envelope is the real win |
| Key encryption keys (KEK) | none (single direct key) | DEK-per-record wrapped by versioned KEK |
| Separate encryption service | in-process | In-house envelope now; Vault Transit = explicit later step |
| Envelope encryption | none | self-describing `v1:<kv>:<wrapped_dek>:<ct>` |
| Master key outside DB | PASS (Vault) | unchanged |
| Key rotation process | none (rotating breaks all ct) | versioned KEK map + re-wrap routine (no plaintext re-encrypt) |
| Emergency key revocation | none | drop a KEK version + re-wrap |
| Divergent key derivation | broker vs LLM diverge | single shared crypto module |
| Never logged / exposed | PASS | unchanged |

## Design

Shared module `src/engine/shared/crypto/` (`credential_cipher.py`):

- New ciphertext format (self-describing, versioned):
  `v1:<key_version>:<urlsafe_b64(wrapped_dek)>:<fernet(dek, plaintext)>`
  - DEK: random Fernet key, one per encrypt call (envelope).
  - wrapped_dek: `Fernet(KEK[key_version]).encrypt(dek)`.
- Legacy format (no `v1:` prefix): decrypted with the direct-Fernet
  path keyed by the current KEK — exactly as today — so every existing
  broker + LLM row keeps decrypting with zero migration.
- KEK resolution (versioned): `BROKER_ENCRYPTION_KEY` is version `1`;
  `BROKER_ENCRYPTION_KEY_V<n>` supplies additional versions. Highest
  configured version is the active write key. Removing a version =
  revocation. Prod/staging fail-fast if no key is set; dev fallback
  retained with a loud warning.
- `rewrap(ciphertext)` upgrades legacy->v1 and re-wraps DEKs to the
  active KEK version without ever touching the plaintext credential
  (rotation is cheap and offline-safe).

## Steps

- [x] 0. Tracker (this file).
- [x] 1. Shared `engine/shared/crypto` module (cipher + versioned KEK + pure funcs). Commit: shared envelope cipher.
- [x] 2. Broker repo -> shared module (local _derive/_encrypt/_decrypt removed; public `decrypt_credential` kept). Reads back-compatible.
- [x] 3. LLM repo -> shared module (DATABASE_URL/hardcoded foot-gun removed; public `decrypt_api_key` kept). Reads back-compatible.
- [ ] 4. DB migration 0033: add `key_version` (smallint, nullable) to broker_connections + llm_connections (operability/observability).
- [ ] 5. Wire `key_version` write-through in both repos on create/update (stamp active_key_version() alongside each new ciphertext).
- [ ] 6. ExternalSecret + Helm values: optional `BROKER_ENCRYPTION_KEY_V<n>` plumbing for rotation.
- [ ] 7. Re-wrap maintenance routine + admin/ops entrypoint (rotation/revocation execution).
- [ ] 8. Final verification pass: grep all consumers, confirm no dead code / mismatch, update this tracker to DONE.

### Verification notes (steps 1-3)
- Back-compat proof: shared cipher normalises BROKER_ENCRYPTION_KEY via
  sha256->urlsafe_b64 (identical to both old _derive funcs) and decrypts
  any non-"v1:" token as a legacy bare-Fernet token, so existing
  broker_connections.{mt5_password_encrypted,ea_auth_token_encrypted}
  and llm_connections.api_key_encrypted rows decrypt unchanged.
- Broker repo: re/logger still used; os removed (only the router reads
  EA env vars, not the repo). No dead imports.
- LLM repo: base64/hashlib/os/Fernet imports removed; none referenced
  elsewhere in the file. No dead imports.
- Public helper names unchanged (decrypt_credential, decrypt_api_key) so
  routers/broker_connections.py, the mt5 factory, and the processor
  config loader need no changes.

## Notes / decisions log

- Fernet retained deliberately (see commit message of this file).
- No re-encryption of existing plaintext required; only optional DEK
  re-wrap on rotation.
- Vault Transit migration intentionally deferred: the envelope design
  makes it a single swap of the KEK-wrap call with no stored-ciphertext
  change. Tracked as a future step, not part of this Tier-3 closure.
