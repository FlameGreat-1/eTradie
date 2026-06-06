# Tier 8 — Order Integrity Hardening (Progress Tracker)

> **CHECKLIST Section 8 — Execution Security / Order Integrity.**
> Branch: `feat/tier8-order-integrity-hardening`.
> This document is the single source of truth for the work. If the
> session is interrupted, the next engineer resumes from the
> **Progress Tracker** without re-deriving anything.

---

## 1. Scope (decided with product owner)

| ID | Finding | In scope? |
|----|---------|-----------|
| **F-1** | "Signed internal execution requests" not implemented (JWT + shared secret only, no payload signature) | ✅ YES |
| **F-2** | "Replay attack protection" only indirect via idempotency (no nonce/timestamp freshness) | ✅ YES |
| **F-5** | gateway↔execution gRPC is plaintext `insecure`; add an app-layer integrity control (the HMAC signature). True mTLS is Tier 9 and tracked separately. | ✅ YES (app-layer only) |
| **F-6** | `SetHaltState` re-read failure echoes zero-values instead of requested intent | ✅ YES |
| **F-7** | Idempotency store-error fall-through to non-idempotent placement has only a WARN log, no metric/alert | ✅ YES |
| F-3 | Strategy kill switch absent (documented out-of-scope, single strategy) | ❌ NO (excluded) |
| F-4 | Kill switch does not flatten open positions (by design) | ❌ NO (excluded) |

---

## 2. Design decisions (TRACED on `main` — verified, not assumed)

### 2.1 Transport: gRPC metadata, NOT proto fields
The committed proto stubs (`proto/execution/v1/*.pb.go`) are hand-maintained
and proto regeneration is a documented post-merge step that **cannot** be run
in this workflow (see kill-switch.md AS-BUILT). Therefore the signature,
timestamp, and nonce travel in **gRPC metadata** on the `ExecuteTrade` call,
exactly as the existing `x-idempotency-key` and `authorization` headers do
(verified in `infra/execution_grpc.go` + `grpc_server.go::incomingIdempotencyKey`).
NO proto change is required.

Metadata keys (lower-case per gRPC convention):
- `x-exec-signature` — hex HMAC-SHA256 over the canonical string
- `x-exec-timestamp` — RFC3339Nano UTC, signer's clock
- `x-exec-nonce`     — the request's idempotency key (see 2.3)

### 2.2 Signing key: reuse `ENGINE_INTERNAL_SHARED_SECRET` (zero new secret)
Both gateway and execution already load `ENGINE_INTERNAL_SHARED_SECRET`
(≥32 chars, Vault-sourced, identical value across services — verified in
`execution/internal/config/config.go` and `gateway` main.go wiring). Reusing
it as the HMAC key means NO new Vault property, NO new ExternalSecret entry,
and the two services are guaranteed to share the key. A dedicated
`EXECUTION_REQUEST_SIGNING_SECRET` override MAY be added later but is not
required for correctness.

### 2.3 Canonical signing string (retry-safe — CRITICAL)
The gateway adapter retries `ExecuteTrade` up to 3× (`resilience.DefaultRetryConfig`,
verified in `pkg/resilience/retry.go` + `infra/execution_grpc.go`). A retry
resends the SAME metadata. The verifier MUST therefore treat a repeated
`(nonce)` carrying an identical canonical hash within the freshness window as
an **idempotent retry (ALLOW)**, and reject only:
  - a signature that does not verify, OR
  - a timestamp outside the freshness window (±skew), OR
  - a nonce reused with a DIFFERENT canonical hash (true replay/tamper).

The nonce is bound to the request's idempotency key (gateway already sets
`x-idempotency-key` = AnalysisID or UUID), so anti-replay state composes
cleanly with the existing `execution_order_idempotency` table semantics and
does not introduce a second, divergent de-dup notion.

Canonical string (ordered, newline-joined, no map iteration nondeterminism):
```
v1\n<timestamp>\n<nonce>\n<user_id>\n<symbol>\n<direction>\n<analysis_id>
```
user_id is taken from the verified JWT claims server-side (NOT from the wire)
so the signature binds the request to the authenticated principal.

### 2.4 Freshness window + nonce store
- Freshness window: `EXECUTION_REQUEST_SIGNATURE_MAX_SKEW_SECS` (default 30s,
  range 5..300). A timestamp older/newer than now±window is rejected.
- Nonce replay store: in-memory TTL set keyed by `(user_id, nonce)` ->
  canonical-hash, TTL = freshness window. Same-hash repeat = allowed retry;
  different-hash repeat = rejected. In-memory is correct because the window
  is seconds and a retry always lands on the same gateway->execution path;
  it is NOT a cross-replica durability requirement (the durable de-dup is the
  Postgres idempotency table, which is the authoritative no-double-fire gate).

### 2.5 Enforcement placement
A SECOND gRPC unary interceptor, chained AFTER `auth.UnaryAuthInterceptor`
(so claims are in context), applied ONLY to `/execution.v1.ExecutionService/ExecuteTrade`
(the money path). Verified the chain is built in `execution/cmd/execution/main.go`
via `grpc.ChainUnaryInterceptor(...)`. Fail-CLOSED: a missing/invalid signature
on ExecuteTrade is `codes.Unauthenticated`/`PermissionDenied`. Gated by
`EXECUTION_REQUIRE_SIGNED_REQUESTS` so a phased rollout is possible
(default: enforce in prod-like envs, warn-only otherwise).

---

## 3. Progress Tracker (update as each step lands)

- [x] **Step 1** — THIS tracker doc (non-functional, recoverable anchor).
- [x] **Step 0b** — Tracing complete. CONFIRMED: gateway exposes
      `cfg.EngineInternalSharedSecret` (`GATEWAY_ENGINE_INTERNAL_SHARED_SECRET`,
      required, >=32 chars); execution exposes `cfg.EngineInternalSecret`
      (same root `ENGINE_INTERNAL_SHARED_SECRET`, same Vault property per the
      execution externalsecret). Execution gRPC chain is
      `grpc.ChainUnaryInterceptor(auth.UnaryAuthInterceptor(...))` — a second
      interceptor can be appended. Gateway adapter retries 3x
      (`resilience.DefaultRetryConfig`) — signature MUST be computed once and
      reused across retries.
- [x] **Step 2 (F-6)** — `grpc_server.go::SetHaltState` now echoes requested
      intent for the written scope on a re-read failure. DONE.
- [x] **Step 3 (F-7)** — `etradie_execution_idempotency_store_errors_total`
      added + incremented at both executor fall-through sites +
      `ExecutionIdempotencyStoreErrors` PrometheusRule alert. DONE.
- [ ] **Step 4 (F-1/F-2/F-5 core)** — new `execution/internal/signing` package
      (HMAC sign/verify + canonical builder + nonce TTL store); config knobs;
      second gRPC interceptor wired in `main.go`.
- [ ] **Step 5 (F-1 gateway side)** — `infra/execution_grpc.go` signs the
      `ExecuteTrade` metadata (retry-safe: sign once, reuse on retries).
- [ ] **Step 6** — unit tests: sign/verify round-trip, skew rejection,
      nonce-replay (same-hash allow / diff-hash reject), retry-safety.
- [ ] **Step 7** — docs: update kill-switch.md cross-ref + this tracker;
      update the audit findings to RESOLVED.

## 4. Definition of done
- Gateway signs every `ExecuteTrade`; execution verifies (fail-closed in prod).
- A captured request replayed with a NEW idempotency key is rejected by the
  signature/nonce gate before any broker work, AND still backstopped by the
  validator + idempotency table.
- Legitimate gateway retries (up to 3×) are NEVER rejected as replays.
- `SetHaltState` re-read failure returns the operator's requested intent.
- Idempotency store-error fall-through is observable + alertable.
- No proto regen required. No new Vault secret required. No dead code,
  no duplicate HMAC helper, no placeholder.
