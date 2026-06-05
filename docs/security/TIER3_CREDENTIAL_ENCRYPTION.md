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
- [x] 4. DB migration 0033: nullable SMALLINT `key_version` on broker_connections + llm_connections (idempotent, 0032 guard pattern).
- [x] 5. key_version wired end to end:
      - 5a ORM column declared on BrokerConnectionRow + LLMConnectionRow (SmallInteger import added to both schemas).
      - 5b write-through: broker create()/update_connection() stamp active_key_version() when encrypting mt5_password/ea_auth_token; LLM create()/create_platform()/update_connection() stamp it on every api_key encrypt.
- [x] 6. Rotation plumbing landed end to end:
      - helm/engine values: `externalSecrets.engine.rotationKeyVersions: []` (default empty), each entry { version>=2, property }.
      - templates/externalsecret.yaml: renders one `BROKER_ENCRYPTION_KEY_V<n>` mapping per declared version (validated: version>=2, property required).
      - deployment already envFroms the engine Secret, so the key reaches the pod as an env var that engine.shared.crypto's BROKER_ENCRYPTION_KEY_V<n> scan picks up -> highest version active.
      - vault-paths/main.tf engine bootstrap string documents broker_encryption_key_v<n> as the rotation property (operator-populated).
- [x] 7. Re-wrap maintenance service + CLI:
      - engine/shared/crypto/rewrap_service.py: CredentialRewrapService walks broker_connections + llm_connections in keyset-paginated batches, re-wraps any legacy / non-active-version column to the active KEK (plaintext never touched), stamps key_version, per-row transaction (resumable), per-column failure isolation, dry_run sizing.
      - engine/shared/crypto/__main__.py: `python -m engine.shared.crypto [--dry-run] [--batch-size N]`; builds DatabaseManager from settings; exit 0 ok / 2 had-failures / 1 fatal.
- [x] 8. Final verification pass complete (see notes below). Tracker DONE.

## STATUS: DONE

### Verification notes (steps 7-8)
- CLI settings attrs verified against config.py: async_database_url
  (property -> str(database_url)), db_pool_size/db_max_overflow/
  db_pool_timeout/db_pool_recycle/db_echo all exist with those names.
- `python -m engine.shared.crypto` correctly executes __main__.py
  (package module path), fixed from the earlier rewrap_service path.
- Broker repo module docstring corrected to describe the shared
  envelope cipher (no longer claims direct-Fernet / identical local
  derivation).
- No remaining importers of the removed _derive_encryption_key in
  either repo; public helpers decrypt_credential / decrypt_api_key kept,
  so routers/broker_connections.py, the mt5 factory, and the processor
  config loader are unchanged.

### Checklist Tier 3 outcome
| Item | Result |
| --- | --- |
| AES-256 at rest | Retained Fernet (AES-128, authenticated) by deliberate decision; envelope is the real hardening. Documented. |
| Key encryption keys (KEK) | DONE - per-record DEK wrapped by a versioned KEK. |
| Separate encryption service | In-house envelope now; Vault Transit is a documented drop-in future step (swap the KEK-wrap call, no stored-ciphertext change). |
| Envelope encryption | DONE - v1:<kv>:<wrapped_dek>:<ct>. |
| Master key outside DB | DONE (already; Vault). |
| Key rotation process | DONE - versioned KEK map + rewrap service, no plaintext re-encrypt. |
| Emergency key revocation | DONE - drop a KEK version after re-wrap. |
| Divergent key derivation | DONE - single shared module; LLM DATABASE_URL/hardcoded foot-gun removed. |
| Never logged / exposed to FE / admin | DONE (already; unchanged). |

### Future (explicitly out of scope, documented for the next tier)
- Vault Transit migration: the VaultClient is KV-v2 only today; moving
  the KEK-wrap step to Transit gives a true separate encryption service
  + AES-256-GCM wrap without touching stored ciphertext. The envelope
  format already isolates the wrap step, so this is a localized change
  in engine.shared.crypto.credential_cipher when prioritised.

### Verification notes (step 6)
- Inert by default: rotationKeyVersions empty -> no extra data keys ->
  no behavioural change. Rotation is an explicit overlay edit.
- ESO-missing-property hazard avoided: versioned keys render only when
  declared, so the steady-state sync never references an absent Vault
  property.
- Wiring is complete with NO pod-spec change because envFrom secretRef
  already exposes every synced Secret key as an env var, and the crypto
  module already discovers BROKER_ENCRYPTION_KEY_V<n>.

### Verification notes (steps 4-5)
- Migration nullable + no server_default: NULL == legacy ciphertext;
  never load-bearing for decryption. Idempotent guards on both tables.
- ORM column added so create_all() (test/dev bootstrap) installs it too,
  keeping migration path and create_all path identical.
- Write-through only stamps when ciphertext is actually written, so the
  version can never drift from the ciphertext it describes.

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
