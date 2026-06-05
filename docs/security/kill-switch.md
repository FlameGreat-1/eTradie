# Execution Kill Switch — Design, Wiring & Continuation Record

> **CHECKLIST Section 8 — Kill Switches.** Branch: `feat/section8-kill-switch`.
> This document is the single source of truth for the feature. It is written
> so that if work is interrupted, the next engineer/session can resume from
> the **Progress Tracker** below without re-deriving anything.

---

## 1. Confirmed semantics (product decision — do not change without sign-off)

A kill switch **halts EXECUTION while ANALYSIS keeps running.** The engine still
performs TA/Macro/RAG/LLM analysis and shows the user what *would* have traded;
only **new order placement** is blocked.

Two scopes:

| Scope | Who controls it | Effect |
|---|---|---|
| **Global** | **Admin only** | Blocks order placement for **all** users, platform-wide. |
| **Per-user** | **User** (own) **+ Admin** (override any user) | Blocks order placement for that one user. |

Rules:
- **No strategy-level switch.** The system runs a single strategy; out of scope.
- **No auto-flatten.** The switch stops *new* orders only. It does **NOT** close
  open positions. Flattening is a separate, deliberate action (not in this work).
- **Global is evaluated before per-user** so the platform-wide reason wins when both are set.
- Industry posture: halt at the boundary **closest to the broker** (execution),
  with a **defense-in-depth** gate at the gateway so we don't even route.

---

## 2. Architecture facts (traced end-to-end in `main` — verified, not assumed)

- **Analysis -> execution handoff is `routing.Router.executeTrade()`** in
  `src/gateway/internal/routing/router.go`, which calls `r.execution.Execute(ctx, decision)`.
  This runs INSIDE the orchestrator's per-symbol pipeline (`orchestrator.processSymbol`
  -> `o.router.Route(...)`), AFTER all analysis. **This is the gateway enforcement point.**
  There is no separate "dispatch" RPC; routing is in-process.
- **`Router.executeTrade` already has a per-user Free-tier execution block** that
  returns a structured `map[string]interface{}{"status":"blocked", ...}` before calling
  execution. The kill-switch gateway gate is modeled on this exact pattern.
- **Execution validator** (`src/execution/internal/validator/validator.go`) runs an
  ordered check slice via `Validate(ctx, req, params *RuntimeParams)`, fail-fast.
  This is the **authoritative backstop** — it also covers resting LIMIT orders and
  armed INSTANT watchers because their fire paths re-validate.
- **Single source of truth = execution `SettingsStore`** (Postgres,
  `src/execution/internal/store/settings.go`). The validator already reads it per-trade
  via `ExecutionServer.resolveRuntimeParams`. The global flag is stored under the
  reserved sentinel user_id `__global__` (`KillSwitchGlobalScope`) in the same
  `execution_settings` table — no schema migration, reuses the `(user_id,key)` unique index.
- **Gateway must NOT keep its own copy** of halt state (no split-brain). It reads the
  execution service's halt state over gRPC and the toggle endpoints WRITE through to
  the execution service. One store, one truth.
- Roles: only `admin` and `etradie`. Admin check pattern in gateway = `RequireAdmin`
  wrapper / `claims.Role == auth.RoleAdmin` (see `admin_quota_handler`, commit `fd399a95`).
- Gateway per-user runtime settings also exist in `src/gateway/internal/settingsstore/store.go`
  (Redis) but are NOT used for the kill switch — execution Postgres is the truth.

---

## 3. Fail-safe posture (decided, documented in code)

- An engaged kill switch is a **durable Postgres row** set deliberately by an operator.
- A transient settings-store **READ error defaults the flag to `false` (NOT halted)**
  and logs WARN. Rationale: a DB blip must not self-inflict a platform-wide outage.
  The gateway is the primary gate; the durable flag is re-read on the next healthy query.
- A **WRITE error on a toggle propagates** to the caller (the API returns 5xx) so an
  operator never believes a halt succeeded when it didn't.

---

## 4. Layers & exact contract

```
  [Client dashboard]  user halt toggle  ---\
  [Admin dashboard]   global/user toggle ---+--> Gateway gRPC (Set/GetHaltState)
                                            |        writes/reads via ExecutionPort
                                            v
  Gateway Router.executeTrade  --(reads halt state)-->  PRIMARY GATE (blocks routing)
                                            |
                                            v   if not halted, Execute(...)
  Execution ExecuteTrade -> Validate -> check0KillSwitch  --> AUTHORITATIVE BACKSTOP
        (reads RuntimeParams.{Global,User}TradingHalted from SettingsStore, Postgres)
```

- **Execution-side terminal outcome:** `OutcomeHalted` -> `StatusHalted` ("HALTED"),
  audit action `EXECUTION_HALTED`, alert `TypeExecutionHalted` (CRITICAL).
- **`check0KillSwitch`** is check number **0** (wired FIRST), pure function reading
  only `RuntimeParams` (no I/O).

---

## 5. Files to touch (complete map)

### Execution (Go) — DONE on this branch
- `src/execution/internal/constants/constants.go` — `CheckKillSwitch=0`, `OutcomeHalted`,
  `StatusHalted`, `ActionExecutionHalted`. **[done]**
- `src/execution/internal/validator/result.go` — `halted()` helper. **[done]**
- `src/execution/internal/store/settings.go` — keys `KeyGlobalTradingHalted`,
  `KeyUserTradingHalted`; `KillSwitchGlobalScope="__global__"`; `Settings` fields;
  `validateSetting`/`applySetting`; `IsGlobalHalted`/`IsUserHalted`/`readHalt`/
  `SetGlobalHalted`/`SetUserHalted`; added `errors` + `pgx` imports. **[done]**
- `src/execution/internal/validator/validator.go` — `RuntimeParams.{Global,User}TradingHalted`;
  `check0KillSwitch` first in chain. **[done]**
- `src/execution/internal/validator/checks.go` — `check0KillSwitch` impl. **[done]**
- `src/execution/internal/server/grpc_server.go` — `resolveRuntimeParams` reads halt flags
  (fail-safe); `outcomeToStatus` maps HALTED; ExecuteTrade halt alert+audit branch. **[done]**
- `src/execution/internal/audit/logger.go` — `LogExecutionHalted`. **[done]**
- `src/alert/event.go` — `TypeExecutionHalted`. **[done]**

### Execution gRPC surface — TODO
- `proto/execution/v1/*.proto` — add RPCs:
  - `GetHaltState(GetHaltStateRequest) returns (GetHaltStateResponse{ bool global, bool user })`
  - `SetHaltState(SetHaltStateRequest{ enum scope[GLOBAL|USER], string target_user_id, bool halted }) returns (SetHaltStateResponse{ bool global, bool user })`
  - Regenerate Go stubs (`make proto` / buf — check repo's proto gen command).
- `src/execution/internal/server/grpc_server.go` — implement `GetHaltState` (calls
  `IsGlobalHalted`+`IsUserHalted`) and `SetHaltState` (calls `SetGlobalHalted`/`SetUserHalted`;
  **enforce: GLOBAL scope requires `claims.Role==admin`**; USER scope requires self OR admin).
  Actor for audit = `claims.UserID`.

### Gateway (Go) — TODO
- `src/gateway/internal/ports/<ports file>` — **FIND IT FIRST** (not at
  `internal/ports/ports.go`; locate the file defining `ExecutionPort` with `Execute` +
  `GetState`). Add to the interface: `HaltState(ctx) (global bool, user bool, err error)`
  and `SetHaltState(ctx, scope, targetUserID string, halted bool) (global, user bool, err error)`.
- Gateway execution client adapter (the concrete `ExecutionPort` impl, likely under
  `src/gateway/internal/infra/` or `.../execution/`) — implement the two new methods by
  calling the new execution gRPC RPCs.
- `src/gateway/internal/routing/router.go` — in `executeTrade`, **before**
  `r.execution.Execute`, add the kill-switch gate (mirror the Free-tier block):
  read `HaltState`; if global -> return `{status:"halted", scope:"global", ...}` + publish
  `TypeExecutionHalted`; else if user -> same with `scope:"user"`. Fail-safe: if the
  `HaltState` read errors, **log and fall through** (execution backstop still enforces).
- `src/gateway/internal/server/grpc_server.go` + `proto/gateway/v1/*.proto` — add RPCs:
  - `SetUserKillSwitch(bool halted)` — client, user-scoped to `claims.UserID`.
  - `SetGlobalKillSwitch(bool halted)` — admin only (role check).
  - `SetUserKillSwitchForUser(target_user_id, bool halted)` — admin override.
  - `GetKillSwitchState()` — returns global + caller's user flag (admin may pass target).
  - Surface state in `GetGatewayConfig` response (add `ExecutionHaltedGlobal` +
    `ExecutionHaltedUser` fields to the proto + handler).
- Gateway HTTP layer (the SPA-facing API; find the handler that maps HTTP->gateway gRPC,
  e.g. admin handler + a client settings handler) — expose:
  - `PUT /api/v1/execution/kill-switch` (client, self) `{ "halted": true|false }`.
  - `PUT /api/v1/admin/execution/kill-switch/global` (admin) `{ "halted": ... }`.
  - `PUT /api/v1/admin/execution/kill-switch/user/{user_id}` (admin override).
  - `GET /api/v1/execution/kill-switch` (state for the dashboard).
  - Reuse the standard chain: authMiddleware -> (RequireAdmin for admin routes) -> csrfMiddleware.
  - **No quick actions / no secrets in code.**

### Observability — TODO
- `src/gateway/internal/observability/` — counter `gateway_execution_halted_total{scope}`
  incremented in the router gate. (Execution side already increments
  `ExecutionTotal{...,"HALTED"}` via the existing outcome label + `validation_rejections{check_0}`.)
- Optional: PrometheusRule alert when a global halt is engaged (info-level, it is deliberate).

### Frontend (separate repo `cotradee/`) — OUT OF SCOPE here, NOTE ONLY
- Add `EXECUTION_HALTED` to `cotradee/src/features/realtime/eventMap.ts` + types.ts.
- Admin dashboard: global + per-user toggle. Client dashboard: own toggle + halted banner.

### Tests — TODO
- `validator` unit test: global halt -> HALTED; user halt -> HALTED; neither -> pass;
  global precedence over user.
- `settings` store test: round-trip Set/IsGlobalHalted + Set/IsUserHalted; missing row=false.
- gateway router test: halted state short-circuits before `execution.Execute`.
- gRPC authz test: non-admin cannot set GLOBAL; user can set own; admin can set any.

---

## 5a. AS-BUILT v2 (FINAL — gRPC + gateway control plane)

This supersedes section 5b below (kept for history). The final design:

**Topology (correct enterprise pattern):**
- **Gateway = sole control plane.** Client + admin HTTP endpoints on the
  gateway, consistent with `admin_quota_handler` / `admin_billing_handler`.
- **Execution = durable owner + final authz.** Exposes two gRPC RPCs
  (`GetHaltState`, `SetHaltState`); owns the settings store; enforces
  authz server-side (global=>admin, user=>self|admin) so the gateway is
  not the only guard (defense-in-depth).
- **Enforcement = `validator.check0KillSwitch`** (authoritative, runs
  first on every trade).
- **Optimization = gateway `Router.executeTrade` primary gate** (blocks
  routing before the gRPC call; fails OPEN to the validator on read
  error so an execution blip is not a routing outage).

**REQUIRES PROTO REGEN:** after merge, run the repo's proto generation
(buf generate / make proto) so `proto/execution/v1/*.pb.go` +
`*_grpc.pb.go` carry the new `GetHaltState`/`SetHaltState` methods and
`GetHaltStateRequest`/`GetHaltStateResponse`/`SetHaltStateRequest`/
`SetHaltStateResponse`/`KillSwitchScope`. The hand-written execution
server impl + gateway adapter compile against those generated symbols.

**Shipped endpoints (gateway):**
- `GET  /api/v1/execution/kill-switch` (auth+CSRF) -> `{ global_halted, user_halted, effective }`
- `PUT  /api/v1/execution/kill-switch` (auth+CSRF) `{ "halted": bool }` -> caller's own switch
- `PUT  /api/v1/admin/execution/kill-switch` (auth -> RequireAdmin -> CSRF)
  `{ "scope":"global"|"user", "halted":bool, "target_user_id":"..." }`

**Files (final):**
- proto: `proto/execution/v1/execution.proto` (RPCs + messages + enum)
- execution gRPC: `server/grpc_server.go` `GetHaltState`/`SetHaltState` + `publishHaltEvent`
- execution validator/settings/constants/audit/alert/metrics: as section 5 [done]
- execution HTTP kill-switch endpoints: **REMOVED** (gateway is sole control plane)
- gateway port: `ports/execution.go` `HaltState`/`SetHaltState`
- gateway adapter: `infra/execution_grpc.go` impl (+`strings` import)
- gateway gate: `routing/router.go` primary gate in `executeTrade`
- gateway control surface: `server/kill_switch_handler.go` (client+admin)
- gateway wiring: `server/http_server.go` (new param) + `container/container.go`

**Frontend (`cotradee/` repo) follow-up:** add `EXECUTION_HALTED` to
eventMap.ts/types.ts; admin toggle -> `PUT /api/v1/admin/execution/kill-switch`;
client toggle+banner -> `GET|PUT /api/v1/execution/kill-switch`.

---

## 5b. AS-BUILT v1 (SUPERSEDED — kept for history)

**Control surface = the EXISTING execution HTTP API server**
(`src/execution/internal/server/http_server.go`, port 8080), NOT new gRPC
RPCs. Reason: the repo ships committed generated protobuf stubs and there
is no way to run `protoc`/buf in this workflow; hand-writing descriptor
bytes would be fragile and is exactly the kind of thing that breaks in
production. The execution HTTP server already has the auth+CSRF chain,
the settings store (single source of truth), and the alert transport, so
it is the correct home.

**Shipped endpoints** (all behind `authMw -> csrfMw`):
- `GET  /api/v1/kill-switch` -> `{ global_halted, user_halted, effective }`
  (any authenticated user; reads own + global).
- `PUT  /api/v1/kill-switch` `{ "halted": bool }` -> toggles the CALLER'S
  own per-user switch (client/eTradie dashboard). User-scoped to
  `auth.UserIDFromContext`.
- `PUT  /api/v1/admin/kill-switch`
  `{ "scope":"global"|"user", "halted":bool, "target_user_id":"..." }`
  -> admin-only (in-handler `claims.Role==auth.RoleAdmin`); flips the
  global switch or any user's switch (admin override).

**Enforcement model (authoritative, single point):** the execution
`validator.check0KillSwitch` (runs FIRST on every trade) reads the halt
flags via `resolveRuntimeParams` from the settings store. Because the
gateway's `Router.executeTrade` already calls `Execute` -> `ExecuteTrade`
-> `Validate`, the validator backstop ALREADY enforces the halt
end-to-end for brand-new entries AND for resting limit orders / armed
instant watchers (their fire paths re-validate). No split-brain: one
Postgres source, one enforcement point.

**Gateway primary gate — INTENTIONALLY DEFERRED.** A gateway-side
short-circuit in `Router.executeTrade` (before the gRPC call) would only
be an OPTIMIZATION (save one round-trip); it is not required for
correctness because the validator is authoritative. Adding it the
"clean" way needs a `GetHaltState` gRPC RPC + stub regen, which is out of
scope for this no-regen change. If desired later: add the RPC to
`proto/execution/v1`, regen, add `HaltState` to `ports.ExecutionPort`
and `ExecutionGRPCAdapter`, then gate in `router.go` (fail-open to the
validator on read error). Documented here so it is a deliberate decision,
not an omission.

**Metric shipped:** `etradie_execution_kill_switch_changed_total{scope,state}`
(toggle actions) + existing `ValidationTotal{result=HALTED}` /
`ExecutionTotal{outcome=HALTED}` / `ValidationRejections{check=check_0}`
for per-trade blocks.

**Frontend (separate `cotradee/` repo) — follow-up:** add `EXECUTION_HALTED`
to eventMap.ts/types.ts; admin toggle UI -> `PUT /api/v1/admin/kill-switch`;
client toggle + banner -> `PUT/GET /api/v1/kill-switch`.

## 6. Progress Tracker (update as you go)

- [x] Step 1 — Execution constants + result helper + settings keys/helpers (+ import fix)
- [x] Step 2 — Execution validator `check0KillSwitch` + RuntimeParams + gRPC resolve/map/alert
- [x] Step 2c — `audit.LogExecutionHalted`
- [x] Step 2d — `alert.TypeExecutionHalted`
- [x] Step 6 — THIS DOC (+ finalized as-built section 5b)
- [x] Step 3 — Control surface: execution HTTP endpoints (client + admin)
      with auth/CSRF chain + in-handler admin check (replaced the gRPC-RPC
      approach; see section 5b for rationale)
- [x] Step 4 — Observability counter `kill_switch_changed_total`
- [x] Step 5 — Tests: `check0KillSwitch` unit tests
- [~] DEFERRED — Gateway primary gate + `GetHaltState` gRPC RPC
      (optimization only; validator backstop is authoritative — section 5b)
- [ ] FOLLOW-UP (separate `cotradee/` repo) — frontend toggles + EXECUTION_HALTED
- [ ] Open MR

## 7. Immediate next action for the resuming session

1. **Locate the `ExecutionPort` interface file** (grep the gateway for `Execute(ctx`
   and `GetState(ctx`). It is NOT `internal/ports/ports.go`.
2. Add proto RPCs `GetHaltState`/`SetHaltState` to `proto/execution/v1`, regenerate stubs.
3. Implement them in execution `grpc_server.go` with the authz rules in section 5.
4. Then proceed down the tracker.

## 8. Definition of done

- Flip user switch -> that user's next analysis still runs, trade is blocked with
  `HALTED`, banner shows; other users unaffected.
- Flip global (admin) -> all users blocked; analysis still runs; non-admin cannot flip it.
- Resting limit orders / armed watchers do not fire while halted.
- Releasing the switch resumes placement on the next trade with no redeploy.
- No split-brain: gateway and execution agree because both read the one Postgres source.
