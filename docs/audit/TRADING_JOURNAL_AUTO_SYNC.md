# Auto-Populate the 90-Day Daily Execution Journal from Manual Trades

**Status:** DESIGN (corrected). Implementation follows in this same MR.
**Supersedes:** the earlier version of this file (which incorrectly
synced ALL managed trades by copying facts into the plan blob).

---

## 1. What we are building (corrected, exact intent)

The Daily Execution Journal (Section 3 of the 90-Day Trading Plan) is
the trader's **manual-trading workbook**. Traders who place trades by
hand are meant to journal each trade daily. Today they fill ALL 25
columns by hand.

We make this easier: **the moment the trader executes a manual trade
and the system reconciles it, a journal row is auto-populated with the
objective facts** (pair, direction, entry, SL, TP, size, then exit /
P&L / R:R / outcome as the trade progresses). The trader then only
fills the **subjective** columns (emotions, trade quality, mistake
category, rule-followed, HTF bias, screenshot, notes).

Hard scoping decisions (corrected):

- **Manual trades ONLY.** System-executed trades are already shown
  elsewhere in the dashboard (management trades view, closed-trade
  journal, PnL calendar, performance metrics). They are EXCLUDED from
  this workbook to avoid duplication.
- **Live, not history backfill.** A row appears when the manual trade
  is ADOPTED (open) and completes through to CLOSE — same-session, as
  they trade. We do NOT use the existing 30-day `MANUAL/RESTORED`
  history import (its entry/SL/TP are zeroed placeholders — see §6).
- **Subjective columns are never auto-filled.** They are the entire
  point of the workbook.

---

## 2. Ground truth (verified against `main`)

### 2.1 The journal rows are an ordered blank list, not date-slots
- Plan owned by the gateway in `src/tradingplan`; persisted as ONE
  JSONB blob per user (`user_trading_plans.plan`, `store.go`).
- `Plan.Journal []JournalRow`, 25 string columns (`models.go`). The
  LLM seeds `JournalSeedDays = 65` BLANK rows. A blank row has no
  date key and no identity — it is simply an empty slot filled in
  order. `Validate()` caps the journal at `journalMaxRows = 200` and
  imposes NO required fields on a row.
- Edits: `PUT /api/v1/trading-plan` -> `UpdatePlanContent` (replaces
  the blob, no version bump).

### 2.2 Manual trades already persist durably in management
- `management_trades` (`src/management/internal/journal/repository.go`),
  one row per managed trade, user-scoped, paginated via
  `GetClosedTrades(limit, offset, ...)`. This is the PERMANENT,
  UNBOUNDED record — it already survives past 90 days.
- Live OPEN trades are in memory in the monitoring `Manager`
  (`GetAllTrades`) and exposed at `GET /api/v1/management/trades`.
- Manual trades are created by the reconciler
  (`monitoring/sync.go buildReconciledTrade`): live-adopted open
  positions get REAL entry/SL/TP/volume and are then managed to a
  real close (exit/PnL/R-multiple). They are tagged
  `Grade = "MANUAL/RECONCILED"`.

### 2.3 The lifecycle hooks (where facts change) — all in sync.go
- **OPEN / adoption:** `processPositionUpdate` "reconcile new orphaned
  positions" loop -> `buildReconciledTrade` -> `RegisterTrade` +
  publishes `alert.TypeTradeSynced` ("External Trade Reconciled").
- **MID-LIFE:** SL/TP modify, volume drift (partial fills), swap/
  commission updates — each persisted via `UpdateTradeRuntime` /
  `UpdateTradeSL`.
- **CLOSE:** position vanishes from broker -> `HandleExternalClose`
  + `RemoveTrade`; the management close path writes `UpdateTradeClose`
  (exit_price, gross_pnl, r_multiple, outcome, closed_at).

### 2.4 The authority boundary (must hold)
- `tradingplan/models.go`: "the engine NEVER consumes it." Layer A
  (AI execution) vs Layer B (human discipline). The journal is a
  one-way SINK: facts flow management -> plan view, never plan ->
  execution.
- The plan store (gateway) and `management_trades` (management) are
  DIFFERENT services / schemas. The bridge is an authenticated
  service call, never a cross-DB join.

---

## 3. Architecture decision: COMPOSITE VIEW, not copy-into-blob

The 90-day-window vs keep-logging-forever tension is resolved cleanly:

- The **permanent, unbounded, paginated** record of every manual
  trade ALREADY exists in `management_trades`. We do NOT copy those
  money facts into the plan blob (that would duplicate money data
  across two services, hit the 200-row cap, and force trimming).
- The **plan stores ONLY the trader's subjective annotations**, keyed
  by `trade_id`. Objective facts are NEVER written into the blob.
- The journal section the trader sees is a **COMPOSITE VIEW**:
  objective facts (from management, for the current 90-day window) +
  the trader's saved subjective fields (from the plan), joined on
  `trade_id`.

Consequences (all desirable):
- No duplication of entry/SL/exit/PnL across services.
- No row-trimming and no 200-row-cap conflict: the cap only ever
  applies to the subjective-annotation rows, and the visible window is
  a date filter over the management record.
- "90-day window" = the journal view shows trades in the current
  90-day window; older trades remain in `management_trades` and are
  reachable by paging the window back (UI affordance), so nothing is
  ever lost.
- The trader's commentary persists independently of the trade facts
  and is keyed by `trade_id`, so it always re-attaches to the right
  trade.

### Why not the simpler copy-into-blob?
Because it duplicates authoritative money data into a second store,
requires reconciliation between the two, and forces the trimming /
cap problem the 90-day window raised. The composite view avoids all
three and keeps a single source of truth for trade facts
(`management_trades`).

---

## 4. The two stored shapes

### 4.1 Subjective annotation (persisted in the plan blob)
Replace the blank-row model for AUTO trades with an annotation list
keyed by trade. Add to `Plan` (schema v1 -> v2):

```
type JournalAnnotation struct {
    TradeID            string `json:"trade_id"`             // management trade ID
    HTFBias            string `json:"htf_bias"`
    RuleFollowed       string `json:"rule_followed"`
    EmotionBeforeTrade string `json:"emotion_before_trade"`
    EmotionAfterTrade  string `json:"emotion_after_trade"`
    TradeQuality       string `json:"trade_quality"`
    MistakeCategory    string `json:"mistake_category"`
    NewsPresent        string `json:"news_present"`
    ScreenshotLink     string `json:"screenshot_link"`
    Notes              string `json:"notes"`
}
```

`Plan.JournalAnnotations []JournalAnnotation` is added alongside the
existing `Journal []JournalRow`. The legacy `Journal` is retained for
fully-manual hand-typed rows (trades the trader logs that the system
never saw, e.g. a different account) so we never remove existing
functionality — it becomes the "manual extra rows" surface, while
AUTO trades use annotations.

### 4.2 Objective facts (NOT stored in the plan; read from management)
pair, direction, style, setup, entry, SL, TP, size, exit, RR planned,
RR achieved, PnL, outcome, date, session — served by a management read
filtered to manual origin + the 90-day window.

---

## 5. Backend changes (typed, no string-matching)

### 5.1 Typed origin discriminator (management)
`grade` is an LLM setup-quality string; overloading it as the
manual/system discriminator is fragile. Add a typed column:

- `management_trades.origin TEXT NOT NULL DEFAULT 'SYSTEM'` with
  CHECK in (`'SYSTEM'`,`'MANUAL_RECONCILED'`,`'MANUAL_RESTORED'`),
  idempotent `ALTER ... IF NOT EXISTS`, backfill existing rows from
  the current `grade` convention
  (`grade LIKE 'MANUAL/RECONCILED%' -> MANUAL_RECONCILED`,
   `grade LIKE 'MANUAL/RESTORED%' -> MANUAL_RESTORED`, else SYSTEM).
- Set it explicitly at every insert:
  `RegisterFilledTrade` -> SYSTEM; `buildReconciledTrade` ->
  MANUAL_RECONCILED; history phase -> MANUAL_RESTORED.
- `TradeRecord` gains `Origin`; `tradeSelectColumns` + `scanTrade`
  add it in lockstep.

### 5.2 Manual-trade read path (management)
The journal view needs BOTH open and closed manual trades in a date
window. Two reads:
- OPEN: filter `Manager.GetAllTrades()` to `origin=MANUAL_RECONCILED`
  (origin must be carried on the in-memory `Trade`; add the field and
  stamp it in `RegisterFilledTrade`/`buildReconciledTrade`/restore).
- CLOSED: new repo method
  `GetManualClosedTrades(ctx, userID, since, until, limit, offset)`
  filtering `origin = 'MANUAL_RECONCILED' AND status='CLOSED'` within
  the window. (Explicitly EXCLUDES MANUAL_RESTORED.)
Expose via a new gRPC RPC `GetManualJournal` on the management service
(or extend `GetTradeJournal` with an `origin` + date filter — decide
in S2; a new RPC is cleaner and avoids changing the dashboard's
existing journal call).

### 5.3 Gateway composite endpoint
- Gateway management client gains a read method calling the new RPC.
- New `GET /api/v1/trading-plan/journal?window=current` (auth+CSRF):
  pulls manual open+closed trades for the window, joins each with the
  user's saved `JournalAnnotation` by `trade_id`, formats objective
  cells deterministically (§7), returns composite rows ordered by
  open time. Pure view; reads management + plan, writes nothing.
- New `PUT /api/v1/trading-plan/journal/annotation`: upsert ONE
  `JournalAnnotation` (subjective fields only) by `trade_id` into the
  plan blob via `UpdatePlanContent`. Rate-limited like the edit path.

### 5.4 Plan model/validation (gateway)
- Add `JournalAnnotations`; bump `CurrentSchemaVersion` to 2.
- Validate annotations: trim cells (120), cap count (200), no banned
  phrases on free-text, no required fields. Keep legacy `Journal`
  validation intact for hand-typed extra rows.

---

## 6. The MANUAL/RESTORED history import (answering "are we importing
manual history?")

YES — today `RunStartupSync` Phase 2 pulls the broker's last 30 days
of closed deals and inserts them as `grade='MANUAL/RESTORED'` rows.
BUT those rows are deliberate approximations: `EntryPrice=0`,
`StopLoss=0`, `TP=0`, `TradingStyle=INTRADAY`, `OpenedAt=closed-1h`,
`DurationMinutes=60` — only symbol/direction/volume/PnL/outcome are
real. They feed the PnL calendar, not the journal.

Decision: the journal view EXCLUDES `MANUAL_RESTORED`. It is incomplete
(no entry/SL/TP/R) and this feature is about recording NEW daily
trades live, not backfilling old ones. If backfill is ever wanted, the
history import must first be upgraded to recover real entry/exit pairs
(separate work, noted, not in scope here).

---

## 7. Deterministic formatting (one gateway helper)
- prices: instrument digits when known, else trim trailing zeros.
- PnL: 2 dp + account/plan currency.
- RR: 2 dp. RiskPercent: as stored (`1%`). Direction: BUY->Long.
- Date/Session: user tz (reuse the pnl-calendar `tz` convention),
  never raw UTC in the visible cell.

---

## 8. Edge cases (all handled)
1. Re-open of the page / re-poll: idempotent — composite view is
   recomputed each request; annotations upsert by `trade_id`.
2. Trade still OPEN: objective close cells (exit/PnL/RR/outcome) show
   blank/"open"; they fill once management closes the trade.
3. Partial closes: ONE journal row per `trade_id`; PnL uses the
   trade row's running `gross_pnl`, RRAchieved uses `r_multiple`.
4. Manual extra rows (hand-typed, no trade): preserved in legacy
   `Journal`; never touched by the composite/auto path.
5. 90-day window exhausted: NOT trimmed — older manual trades stay in
   `management_trades`; the UI pages the window back. Annotation list
   is capped at 200 (subjective rows only); when full, oldest
   annotations for trades outside the window can be pruned safely
   because the objective facts remain in management.
6. System trades: excluded by `origin=MANUAL_RECONCILED` filter.
7. MANUAL_RESTORED: excluded (§6).
8. Authority boundary: read-only into the plan view; nothing flows
   back to execution.

---

## 9. Frontend changes
- `types/index.ts`: add `JournalAnnotation`; composite row type.
- `JournalSection.tsx`: render objective cells read-only (from the
  composite endpoint) with a "synced" badge; keep subjective cells
  editable -> `PUT .../annotation`; window selector (current 90d /
  previous). last-synced indicator.
- `lib/excel.ts`: export the composite (objective + subjective);
  omit internal `trade_id` from the printed sheet.
- `api/client.ts` + `hooks.ts`: composite GET + annotation PUT hooks;
  invalidate on save.

---

## 10. Implementation checklist (commit steps, this MR)
  [x] S1 management: typed `origin` column + idempotent migration +
         backfill; `TradeRecord.Origin` + select/scan; stamp origin at
         all three inserts; add `Origin` to in-memory `Trade` +
         restore + reconciler. DONE — schema/model/repository in
         lockstep; InsertTrade defaults blank->SYSTEM; RegisterFilled
         Trade=SYSTEM, buildReconciledTrade bare=MANUAL_RECONCILED &
         recovery=rec.Origin, history=MANUAL_RESTORED; restore carries
         it.
  [x] S2 management: `GetManualClosedTrades(window)` repo method +
         `GetManualJournal` gRPC RPC (manual+window, excludes
         RESTORED) returning open+closed manual trades. DONE — proto
         RPC + messages added (run `make proto-gen`); repo query +
         grpc handler (open from monitor filtered to
         origin=MANUAL_RECONCILED + closed from store) + mock/import
         fixes. REQUIRES `make proto-gen` before this compiles.
  [ ] S3 gateway: management client read method; plan model
         `JournalAnnotations` + schema v2 + validation.
  [ ] S4 gateway: `GET /trading-plan/journal` composite + formatter;
         `PUT /trading-plan/journal/annotation` upsert.
  [ ] S5 frontend: composite view, editable subjective cells, window
         selector, excel, hooks.
  [ ] S6 tests: origin backfill, manual-only filter, window paging,
         annotation upsert idempotency, open->close cell fill,
         RESTORED exclusion, formatting.
  [ ] S7 metrics + flip this doc to DONE.

---

## 11. Non-goals
- Feeding the journal back into AI analysis/execution (forbidden).
- Auto-filling subjective columns.
- Including system-executed trades (shown elsewhere).
- Backfilling MANUAL_RESTORED history (incomplete; separate work).
- Changing how the LLM generates the plan; this runs on the
  persisted plan + the live management record.
