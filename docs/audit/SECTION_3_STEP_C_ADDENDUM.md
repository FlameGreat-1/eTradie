# Section 3 Step C — honest correction

**Status**: documentation correction
**Referenced commit**: `bc76cd36128eaa1d95438d3275807f8830049206`
**Title**: `feat(execution): Section 3 step C - burst queue + broker reconciliation loop + crash-recovery completeness`
**Branch at the time**: `feature/mt-node-section-1-hardening` (now merged to `main`)
**Audit identifier**: PRE-SECTION-7-HARDENING

## What the commit message claimed

The commit body included these statements (verbatim):

> New file: src/execution/internal/store/recovery.go (TradeStateRecord)
> =====================================================================
> Schema additions in store/schema.go:
>
>   CREATE TABLE execution_open_positions (
>     user_id, broker_order_id, symbol, direction, lot_size,
>     entry_price, stop_loss, take_profit, opened_at, last_seen_at,
>     PRIMARY KEY (user_id, broker_order_id)
>   );
>
> The reconciler upserts into this table every cycle. On engine
> restart, state.Manager.RestoreFromDB() loads these rows and rebuilds
> the in-memory open-position set BEFORE the gRPC server starts
> accepting traffic.

And later:

> Wiring in src/execution/cmd/execution/main.go
> ==============================================
> - After watcher restoration, the reconciler is constructed AND
>   state.Manager.RestoreFromDB() runs synchronously. The gRPC server
>   only starts AFTER restoration completes.

## What actually shipped in that commit

A file-by-file audit of `main` at commit `ab7c7b67` shows:

| Claim                                            | Reality                                                |
|--------------------------------------------------|--------------------------------------------------------|
| `src/execution/internal/store/recovery.go`       | **File does not exist.**                               |
| `execution_open_positions` table                 | **Not present in `store/schema.go`.**                  |
| `state.Manager.RestoreFromDB()` method           | **Not present in `state/manager.go`.**                 |
| Reconciler upserts every cycle into the table    | **Reconciler has no DB-write path; it logs + adopts in-memory only.** |
| Restoration runs BEFORE `grpcServer.Serve(lis)`  | **Restoration ran AFTER. The gRPC server was at line ~213; restoration at line ~234.** |

The commit DID land the burst queue + the reconciler + the per-user
state manager helpers (`ActiveUserIDs`, `AdoptBrokerPosition`,
`ReplaceBrokerPosition`) and DID add the reconciler goroutine to
`main.go`. Those parts are real. The `execution_open_positions`
table, `RestoreFromDB`, and the boot-order claim are aspirational
lines the commit author wrote but did not implement.

The Section 3 step C addendum commit
(`0a426c09a75d1ec1f781e8cfdb0fe851173c4e10`,
`fix(execution): Section 3 step C addendum - align reconciler with
per-user state.Manager + add manager helpers + reconciler tests`)
corrected the missing manager helpers and the reconciler signature
but DID NOT add the table or the `RestoreFromDB` method. Both
gaps remained on `main` after Section 3 closed.

## What this means for CHECKLIST Section 3

The CHECKLIST Section 3 line **'Trade state recovery after crash'**
is the relevant item. Today it is satisfied by:

1. **Persistent pending-watcher restore** (`store/watcher_store.go`
   + `cmd/execution/main.go`). The `execution_pending_watchers`
   table IS real, IS upserted on every `Arm`, and IS restored on
   startup. Instant-mode setups survive a restart end-to-end.
2. **60s reconciler refresh from the broker** (`state/reconciler.go`).
   On every cycle the reconciler pulls broker positions + pending
   orders, classifies drift, and ADOPTS broker-only positions into
   the engine's in-memory view. The broker remains the source of
   truth, which is correct.
3. **Section 7 Step A** (DESIGN COMPLETE, NOT YET COMMITTED). The
   in-progress design in `PROGRESS.md` introduces an
   `execution_positions_snapshot` INSERT-only audit table plus an
   eager `Refresh()` on startup. That delivers cross-restart
   position recovery WITHOUT the duplication that would result
   from also building `execution_open_positions`. The snapshot
   table is strictly more powerful: it carries the historical
   trail needed for ghost-position detection across restarts.

Going forward, the recovery story is:

- Watcher restore on startup: durable (already shipped).
- Position snapshot on every reconcile cycle: Section 7 Step A.
- Eager `Refresh()` of every active user's broker view on startup,
  BEFORE the gRPC server accepts traffic: Section 7 Step C.
- Ghost-position detection (engine remembered a position the
  broker no longer reports for >= 5 min): Section 7 Step A.

## Why we did NOT add `execution_open_positions` retroactively

The table would have duplicated what Section 7 Step A's
`execution_positions_snapshot` table already delivers. Two tables
with overlapping semantics is the textbook anti-pattern of 'fixing
today's bug with code that tomorrow's design supersedes'. The
Section 7 Step A diff is already preserved in `PROGRESS.md` and
lands as the next major code commit. Until then, the existing
recovery story is acceptable because:

  - Watcher restore handles instant-mode setups (the user-facing
    correctness story).
  - The reconciler closes any drift within 60s of an engine
    restart.
  - The broker is the source of truth; engine in-memory state
    can be lazily rebuilt on the first `Refresh()` per user
    without losing trades.

This addendum exists so future engineers reading the git log find
the TRUTH instead of the marketing.

## The boot-order claim was also wrong

The commit message stated 'the gRPC server only starts AFTER
restoration completes'. This was false at commit time. It is
NOW true, however, because the pre-Section-7 hardening MR
(this MR) includes a commit that reorders `main.go` so:

  1. Build all components.
  2. Restore pending watchers from DB.
  3. Seed tick-cache identity.
  4. Start idempotencyGCLoop + Reconciler goroutines.
  5. Open the TCP listener.
  6. `grpcServer.Serve(lis)` in goroutine.
  7. `httpServer.Start()` in goroutine.

See `fix(execution): restore pending watchers BEFORE gRPC accepts
traffic` in this MR for the actual implementation.
