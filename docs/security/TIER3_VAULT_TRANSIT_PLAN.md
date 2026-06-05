# Tier 3 follow-up: Vault Transit KEK ("separate encryption service")

Status: **PLANNED / awaiting go-ahead + availability decision.**

This is the single remaining open line on CHECKLIST.md Tier 3. Everything
else (AES-256-GCM data layer, envelope, KEK, rotation, revocation,
unified derivation, master-key-outside-DB, never-logged/exposed) is DONE
in MR !88. See `TIER3_CREDENTIAL_ENCRYPTION.md`.

## What "separate encryption service" means here

Today the KEK that WRAPS each per-record DEK is an in-process Fernet key
derived from a Vault-delivered secret. The key material lives in engine
pod memory. "Separate encryption service" means the wrap/unwrap happens
in a dedicated service that holds the KEK and never exposes it -- i.e.
**HashiCorp Vault Transit** (already our secrets backend). The engine
sends the DEK to Transit to wrap/unwrap; the KEK never leaves Vault.

The v2 envelope already isolates the wrap step, so ONLY the DEK-wrap and
DEK-unwrap calls change. Stored ciphertext format and the AES-256-GCM
data layer are untouched.

## Why it is a separate, tested MR (not a tack-on)

1. **Async ripple.** `encrypt_credential` / `decrypt_credential` /
   `decrypt_api_key` are SYNCHRONOUS today and are called inline by:
     - `routers/broker_connections.py` (async handlers -- OK to await)
     - `engine/ta/broker/mt5/factory.py::create_mt5_broker_from_connection`
       (SYNC; called from async router after a sync decrypt)
     - the processor config loader (`decrypt_api_key`) 
     - `engine/shared/crypto/rewrap_service.py` (async -- OK to await)
   A Transit wrap is a network call, so the cipher API must become
   async and every caller + its callers must `await`. That is a wide,
   mechanical change that needs its own review + tests.

2. **Money-path availability (THE decision to make).** Broker-credential
   decryption is on the trade execution path. If every decrypt does a
   live Transit call, a Transit outage HALTS TRADING -- a worse failure
   than today's in-process key. The correct enterprise pattern (AWS KMS
   SDK, Google Tink, Vault guidance) is:
     - Transit WRAPS the DEK (KEK never leaves Vault).
     - The engine CACHES the unwrapped DEK in memory per-record for a
       short bounded TTL, so steady-state decrypt is LOCAL and a Transit
       blip does not halt trading.
     - Transit is hit only on cache miss / new encrypt / rotation.
   The operator must explicitly choose the cache TTL and the
   fail-open-vs-fail-closed posture on a Transit outage with a cold
   cache. That is a business/risk decision, not a code default.

## Concrete implementation scope (when greenlit)

### A. Terraform (`infrastructure/cluster/vault-paths/`)
  - New `vault_mount` of type `transit` (e.g. `etradie-transit`).
  - `vault_transit_secret_backend_key` for credential KEK
    (`broker-cred-kek`), `type=aes256-gcm96`, `deletion_allowed=false`,
    rotation enabled (Transit rotates the key version natively -- this
    SUPERSEDES the env-var BROKER_ENCRYPTION_KEY_V<n> rotation once
    migrated).
  - `vault_policy` granting the engine SA `update` on
    `<mount>/encrypt/broker-cred-kek` and `<mount>/decrypt/broker-cred-kek`
    (+ `rewrap` for rotation). NO `read` on the key itself.
  - Bind to the existing engine K8s auth role (the engine SA already
    authenticates to Vault for the mt-node provisioner path).

### B. VaultClient (`engine/shared/vault/client.py`)
  - Add async `transit_encrypt(key, plaintext_b64)` and
    `transit_decrypt(key, ciphertext)` (+ optional `transit_rewrap`).
    Reuses the existing K8s-auth token caching + retry plumbing.

### C. credential_cipher.py (v3 scheme)
  - New `v3` scheme: the DEK is wrapped by Transit instead of the local
    Fernet KEK. Format carries the Transit key ref + Transit ciphertext
    of the DEK; the data layer stays AES-256-GCM (unchanged).
  - `decrypt()` reads v3 AND v2 AND v1 AND legacy (zero migration).
  - Bounded in-memory DEK cache (LRU + TTL) keyed by wrapped-DEK.
  - Cipher API becomes async; `get_cipher()` injected with the
    VaultClient (no longer pure-env). A no-Transit dev/test fallback
    keeps v2 (local KEK) so docker-compose/pytest run without Vault.
  - `needs_rewrap()` flags v1/v2/legacy -> upgrade to v3; the existing
    re-wrap job migrates rows with no plaintext re-encrypt.

### D. Call-site async conversion
  - Await the cipher in both repos, the mt5 factory, the processor
    config loader, and the rewrap service. Mechanical but must be
    complete (a missed sync call = a coroutine stored as ciphertext).

### E. Tests
  - Round-trip v3; decrypt of v1/v2/legacy after enabling Transit;
    cache hit/miss; Transit-outage behaviour under the chosen posture;
    rewrap v2 -> v3.

## Decision required from the operator before build

1. Go-ahead to make the cipher API async (touches ~5 call sites).
2. DEK cache TTL (proposed: 300s) and max size (proposed: 2048 entries).
3. Fail posture on Transit outage with a COLD cache:
   - fail-closed (safer; a Transit outage blocks NEW credential reads), or
   - fail-open is NOT possible for decrypt (no key = no plaintext), so
     the real lever is the cache TTL: a longer TTL = longer ride-through
     of a Transit outage at the cost of slower key-revocation propagation.

Until these are decided, shipping Transit would either (a) risk halting
trading on a Transit blip, or (b) bake in a TTL/posture the business has
not signed off. Hence this is staged as its own MR.
