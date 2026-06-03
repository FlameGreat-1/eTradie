# Auto-Sync Broker Trades into the 90-Day Trading Journal

**Status:** DESIGN ONLY (no code changed). Implementation plan for review.
**Scope:** auto-populate Section 3 (Daily Execution Journal) of the
LLM-generated 90-Day Trading Plan from trades the system already
records — both system-executed and manually-executed/reconciled —
leaving only the subjective columns for the trader to fill in manually.

---

## 1. Goal (in plain terms)

Today the trader fills the entire 90-day Daily Execution Journal **by
hand**. Many of its columns are objective facts the platform ALREADY
knows for every managed trade (date, pair, direction, entry, SL, TP,
exit, P&L, R:R, outcome, etc.) — including manually-executed trades,
because the management reconciler adopts and manages them (see
`src/management/internal/monitoring/sync.go`).

This design auto-fills those known columns the moment a trade closes,
so the trader only types the **subjective** fields (emotions, trade
quality, mistake category, rule-followed, HTF bias notes, screenshot,
free-text notes). This mirrors how TraderVue / Edgewonk / Tradezella
auto-import broker fills and leave journaling commentary to the user.

---

## 2. Ground truth (verified against `main`)

Every statement below was read from source, not assumed.

### 2.1 Where the journal lives
- The 90-day plan is owned by the **gateway** service in
  `src/tradingplan` (package `tradingplan`).
- Persistence: ONE JSONB row per user in `user_trading_plans.plan`
  (`src/tradingplan/schema.go`, `store.go`). `Plan.Journal` is
  `[]JournalRow` (`models.go`).
- A `JournalRow` has **25 string columns** (`models.go`): `Date,
  Session, Pair, Direction, Style, SetupType, HTFBias, Entry,
  StopLoss, TakeProfit, RiskPercent, PositionSize, Exit, RRPlanned,
  RRAchieved, PnL, Outcome, RuleFollowed, EmotionBeforeTrade,
  EmotionAfterTrade, TradeQuality, MistakeCategory, NewsPresent,
  ScreenshotLink, Notes`. All are free-text strings; the LLM seeds 65
  blank rows (`JournalSeedDays = 65`).
- Edits happen via `PUT /api/v1/trading-plan` ->
  `Handler.putPlan` -> `Store.UpdatePlanContent` (replaces the JSONB
  blob, does NOT bump `version`; version is reserved for full LLM
  regenerations). Validation: `Validate()` in `validation.go` trims
  every cell to 120 chars, caps the journal at 200 rows, and enforces
  NO required fields on a journal row (so a partially-filled synced
  row is structurally valid).

### 2.2 Where the trade data lives
- Closed trades live in the **management** service DB table
  `management_trades` (`src/management/internal/journal/repository.go`),
  one row per managed trade, scoped by `user_id`.
- `GetClosedTrades(ctx, userID, limit, offset, symbolFilter,
  styleFilter)` already returns the closed-trade projection.
- Management already exposes it to the dashboard at
  `GET /api/v1/management/journal`
  (`src/management/internal/http/server.go handleGetJournal`),
  returning per-trade: `trade_id, symbol, direction, entry_price,
  exit_price, stop_loss, lot_size, gross_pnl, r_multiple,
  confluence_score, grade, setup_type, trading_style, outcome,
  duration_minutes, sl_adjustment_count, partial_close_count,
  analysis_id, opened_at, closed_at`.
- Manually-executed trades ARE in this table: the reconciler
  (`sync.go buildReconciledTrade`, post-EM-F2) inserts them and the
  management worker manages + closes them, so they flow into
  `management_trades` exactly like system trades. They carry
  `grade = "MANUAL/RECONCILED"`, which is how we tag a synced row's
  origin.

### 2.3 The hard architectural constraint (must not be violated)
- `src/tradingplan/models.go` package doc: **"the engine NEVER
  consumes it [the plan]"**, and authority separation:
  Layer A (Trading System) governs AI execution; Layer B (Trading
  Plan) governs human discipline. **The journal must remain a
  one-way SINK.** Auto-sync may only WRITE facts INTO the journal; it
  must NEVER read the journal back into analysis/execution. This
  design preserves that: data flows management -> plan, never the
  reverse.
- The two stores are in **different services and (logically)
  different schemas**: the plan is in the gateway's `user_trading_
  plans`; trades are in management's `management_trades`. No
  cross-table SQL join is possible or allowed; the bridge is an
  authenticated service call (the same boundary the dashboard already
  uses), NOT a DB mix-up.

---

## 3. Column mapping (objective vs subjective)

For each of the 25 `JournalRow` columns, the source we can auto-fill
from a closed `management_trades` row, or `MANUAL` if it is inherently
subjective and must stay user-filled.

| JournalRow column      | Auto-sync source (management closed trade)                         |
|------------------------|--------------------------------------------------------------------|
| `Date`                 | `closed_at` (date part, user tz) — fall back to `opened_at`        |
| `Session`              | `session` if present; else derive from `opened_at` hour (UTC)     |
| `Pair`                 | `symbol`                                                           |
| `Direction`            | `direction` (BUY/SELL -> Long/Short)                              |
| `Style`                | `trading_style`                                                   |
| `SetupType`            | `setup_type`                                                      |
| `HTFBias`              | **MANUAL** (not captured per-trade; trader's read)               |
| `Entry`                | `entry_price`                                                     |
| `StopLoss`             | `stop_loss` (initial SL on the row)                              |
| `TakeProfit`           | `tp1_price`/`tp2`/`tp3` — see note; or final exit target          |
| `RiskPercent`          | `risk_percent` (present on the trade row)                        |
| `PositionSize`         | `lot_size` (`total_lot_size`)                                    |
| `Exit`                 | `exit_price`                                                     |
| `RRPlanned`            | `rr_ratio` (present on the trade row)                            |
| `RRAchieved`           | `r_multiple`                                                     |
| `PnL`                  | `gross_pnl`                                                      |
| `Outcome`              | `outcome` (WIN/LOSS/BREAKEVEN)                                   |
| `RuleFollowed`         | **MANUAL** (self-assessment)                                     |
| `EmotionBeforeTrade`   | **MANUAL**                                                       |
| `EmotionAfterTrade`    | **MANUAL**                                                       |
| `TradeQuality`         | **MANUAL**                                                       |
| `MistakeCategory`      | **MANUAL**                                                       |
| `NewsPresent`          | **MANUAL** (not stored per-trade today; could derive later)      |
| `ScreenshotLink`       | **MANUAL**                                                       |
| `Notes`                | **MANUAL**                                                       |

Note on `TakeProfit`: the closed-trade projection in
`GetClosedTrades` does NOT currently select the tp* columns (they
exist on the row but are not in the closed projection). Two options in
section 6.

**16 of 25 columns auto-fill; 9 stay manual.** The 9 manual ones are
exactly the discipline/psychology fields the journal exists to
capture, so the human value of the workbook is fully preserved.

---

## 4. Design decision: how a synced row coexists with manual edits

The single hardest correctness question. A `JournalRow` today has no
identity, so we cannot tell a synced row from a hand-typed one, and a
re-sync must not (a) duplicate a trade, nor (b) clobber the trader's
subjective edits.

**Decision: add a stable per-row identity + an `auto` origin flag, and
merge by identity.**

- Add two fields to `JournalRow` (schema-versioned, see section 5):
  - `TradeID string json:"trade_id"` — the management trade ID for
    synced rows; empty for hand-added rows.
  - `Source string json:"source"` — `""`/`"manual"` for user rows,
    `"auto"` for synced rows.
- **Merge rule on sync:** for each closed management trade not already
  represented (match on `trade_id`), INSERT a new row with the
  objective columns filled and the subjective columns blank. For a
  trade already represented, UPDATE ONLY the objective columns and
  leave every subjective column untouched (never overwrite trader
  input). This is an idempotent upsert keyed by `trade_id`.
- Hand-added rows (`trade_id == ""`) are never touched by sync.

This guarantees: no duplicates, no lost commentary, re-running sync is
safe, and the trader can still freely add fully-manual rows.

---

## 5. Schema / contract changes (typed, versioned)

1. `src/tradingplan/models.go`
   - Add `TradeID` and `Source` to `JournalRow`.
   - Bump `CurrentSchemaVersion` 1 -> 2 (a field was added). Existing
     rows unmarshal with the two new fields empty, which is the
     correct "manual, un-synced" state, so no data migration is
     needed — older plans simply have all-manual rows until first
     sync.
2. `src/tradingplan/validation.go`
   - Trim/cap the two new cells (`trade_id`, `source`) like every
     other cell; add `source` to an allowed-value check (`""`,
     `"manual"`, `"auto"`). No new required fields.
3. Frontend types (`cotradee/src/features/tradingplan/types/index.ts`)
   - Mirror the two new fields so the editor and Excel export round-
     trip them. The JSON contract is hand-synced across Go + TS here
     (same drift risk as `ProcessorOutput`); keep them in lockstep.

No change to `user_trading_plans` SQL DDL: the plan is a JSONB blob,
so new struct fields need no `ALTER`.

---

## 6. Where the sync runs (the integration point)

Three options were considered against the service boundaries that
actually exist. The two stores are in different services, so the sync
must cross that boundary via an authenticated call, never a DB join.

### Option A (RECOMMENDED) — gateway pull, on demand + on plan open
The gateway already owns the plan and already holds a management gRPC
client (`src/gateway/internal/management/client.go`, currently only
`RegisterFilledTrade`). Add a read path:

1. Extend the gateway's management client with
   `GetClosedTrades(ctx, userID, since)` backed by the management
   gRPC `GetTradeJournal` RPC (already defined in
   `proto/management/v1` and implemented by
   `ManagementServer.GetTradeJournal`). No new management endpoint
   needed for the basic mapping.
2. New gateway endpoint `POST /api/v1/trading-plan/sync-journal`
   (auth + CSRF, rate-limited like the other plan mutations):
   - load the user's plan (must be `active`),
   - pull closed trades for the user,
   - run the idempotent merge from section 4,
   - persist via `Store.UpdatePlanContent` (no version bump — a sync
     is not a regeneration),
   - return the updated plan.
3. The SPA calls it when the user opens the Trading Plan page and
   exposes a "Sync trades" button for an explicit refresh.

Pros: respects the one-way boundary; reuses the existing gRPC RPC and
the existing plan store; no new background workers; the gateway is
already the plan's owner. Cons: sync is pull-triggered (on page open /
button), not instant on close — acceptable, and avoids a push
dependency from management into the gateway plan store.

### Option B — management push on close
When a trade closes (`UpdateTradeClose`), management calls a new
gateway internal endpoint to upsert the journal row. Gives
near-instant sync. Cons: makes management depend on the gateway plan
store (new coupling + new internal auth surface), and management would
need the user's plan existence/tz — more moving parts for marginal
latency benefit. Recorded as a possible future enhancement on top of
Option A.

### Option C — frontend-only merge
The SPA already fetches `/api/v1/management/journal` and the plan;
it could merge client-side and PUT the plan. Cons: puts money-bearing
merge logic in the browser, races between tabs, and trusts the client
to write authoritative rows. Rejected.

**Chosen: Option A.**

### TakeProfit / tp-columns gap (from section 3 note)
`GetClosedTrades` does not select the `tp1/2/3_price` columns. For the
`TakeProfit` journal cell, either:
- (A1) use `exit_price` as the realized target text (simplest, always
  available), or
- (A2) extend the `GetClosedTrades` SELECT + the `GetTradeJournal`
  proto/projection to carry `tp1_price` so the cell shows the planned
  TP.
Recommend A1 for v1 (exit is the truth of what happened) and A2 as a
follow-up if the planned TP is wanted alongside the realized exit.

---

## 7. Field formatting rules (no lossy coercion)

The journal columns are strings the UI renders verbatim, so the sync
must format numbers deterministically (no scientific notation, broker-
appropriate precision):
- prices (`Entry/StopLoss/Exit`): format with the instrument digits
  when known, else trim trailing zeros.
- `PnL`: 2 decimals with the account currency where known.
- `RiskPercent`: render as the stored percent (e.g. `1%`).
- `RRPlanned`/`RRAchieved`: 2 decimals (e.g. `3.00`, `2.41`).
- `Direction`: BUY->`Long`, SELL->`Short` to match the workbook tone.
- `Date`/`Session`: resolved in the user's timezone (the PnL-calendar
  endpoint already takes a `tz` param; reuse the same convention).
All formatting lives in ONE gateway helper so it cannot drift.

---

## 8. Edge cases (must all be handled)

1. **Re-sync idempotency** — merge keyed by `trade_id`; objective-only
   update; never touch subjective cells. (Section 4.)
2. **200-row cap** (`journalMaxRows`) — when synced + manual rows would
   exceed 200, keep the most recent by close date; surface a notice so
   the trader knows older auto rows were trimmed. Never silently drop a
   row that contains manual commentary (prefer trimming blank auto
   rows first).
3. **No plan yet** (`status != active`) — sync is a no-op with a clear
   message: generate a plan first. (The plan must exist to hold rows.)
4. **Blank LLM-seeded rows** — the LLM seeds 65 empty rows. First sync
   should fill blank seed rows before appending new ones, so the
   workbook does not balloon with empties + duplicates. Define "blank"
   as a row with empty `trade_id` AND empty objective cells.
5. **Manual trades** — included; tagged `Source="auto"`,
   `Style` may be `POSITIONAL` (the reconciler default) and `SetupType`
   may be empty. Those cells sync as-is; the trader can correct them.
6. **Partial closes / multi-leg** — one journal row per management
   trade (`trade_id`), not per partial. `PnL` = `gross_pnl` (already
   the summed realized P&L on the row), `RRAchieved` = `r_multiple`.
7. **Timezone** — date/session resolved in the user's tz (same param
   the pnl-calendar endpoint uses); never raw UTC in the visible cell.
8. **Currency** — P&L currency from the plan's `BalanceCurrency` when
   the trade row does not carry one.
9. **Authority boundary** — sync only writes into the plan; nothing
   reads the plan back into execution. (Section 2.3.)

---

## 9. Frontend changes

- `cotradee/src/features/tradingplan/types/index.ts`: add `trade_id`,
  `source` to the journal row type.
- `JournalSection.tsx`: render auto-filled cells distinctly (e.g. a
  subtle "synced" badge / read-only style on objective columns of
  `source=="auto"` rows) while keeping subjective columns editable;
  show a "Sync trades" button + last-synced timestamp.
- `lib/excel.ts`: include the new columns in export (or deliberately
  omit `source`/`trade_id` from the printed sheet — decide; recommend
  omitting both from the printed export, keeping them only in the
  stored JSON).
- `api/client.ts` + `api/hooks.ts`: add the `sync-journal` call + a
  hook; invalidate the plan query on success.

---

## 10. Implementation checklist (for a future MR, in commit steps)

  [ ] S1 models: add `TradeID`/`Source` to `JournalRow`; bump
         `CurrentSchemaVersion` to 2; extend `validation.go`
         (trim + `source` allowed-values; no new required fields).
  [ ] S2 gateway management client: add `GetClosedTrades` over the
         existing `GetTradeJournal` gRPC RPC.
  [ ] S3 gateway sync service: deterministic formatter (section 7) +
         idempotent merge (section 4) + edge cases (section 8).
  [ ] S4 gateway endpoint `POST /api/v1/trading-plan/sync-journal`
         (auth + CSRF + rate limit) -> merge -> `UpdatePlanContent`.
  [ ] S5 (optional A2) extend closed-trade projection with tp1_price
         if the planned TP cell is wanted alongside the exit.
  [ ] S6 frontend: types + JournalSection sync UI + hook + excel.
  [ ] S7 tests: merge idempotency, subjective-preservation, row-cap
         trimming, blank-seed fill, tz/currency formatting.
  [ ] S8 metrics + docs: a sync counter; update this doc's status.

---

## 11. Explicitly OUT of scope / non-goals

- Feeding the journal back into AI analysis or execution (forbidden by
  the Layer A / Layer B authority separation).
- Auto-filling the subjective columns (emotions, quality, mistakes,
  rule-followed, screenshot, notes) — those are the trader's job and
  the reason the workbook exists.
- Auto-generating `NewsPresent` / `HTFBias` in v1 (not stored per
  trade today; possible future enrichment from the macro/TA layer,
  still written one-way into the journal).
- Any change to how the LLM GENERATES the plan; sync runs after
  generation, on the persisted plan.
