# Journal Auto-Fill — Round-2 Audit (post #1-#8 merge)

**Status:** IN PROGRESS. Second end-to-end audit of the manual-trade
Daily Execution Journal auto-fill after the first hardening pass merged.

## Findings

- **A (reviewed, not a bug)** — `applyObjectiveCells` rewrites the
  objective cells from the management fact on every load, including
  blanking the close cells (Exit/RRAchieved/PnL/Outcome) while the
  trade is open. This is correct: objective cells are system-owned and
  the trader only owns the subjective cells. No change.
- **B (BUG — silent data loss)** — in `mergeManualTrades`, when there is
  no blank row and `len(Journal) >= journalMaxRows` (200), the manual
  trade is dropped via a bare `continue` with no log / metric / signal.
  A heavy journal (seed rows + hand-typed rows + many trades) therefore
  permanently STOPS auto-filling new manual trades, invisibly. Must be
  surfaced (metric + log) and the cap headroom reconsidered.
- **C (BUG — unobservable)** — the auto-fill path emits no metrics at
  all: no count of rows filled / updated / appended, no count of
  cap-hit drops (B), no reader-error counter. Every other trading-plan
  path is instrumented with promauto counters. Add them.
- **D (reviewed, not a bug)** — `formatStyle` uses `lower[:1]` which is
  safe for the ASCII trading-style enum (SCALPING/INTRADAY/SWING/
  POSITIONAL/MANUAL...). No change.
- **E (minor)** — `tradingplanadapter.ManualTrades` requests the closed
  set with a hardcoded `Limit: 500, offset 0` and never paginates, so
  a user with >500 closed manual trades silently truncates. Align the
  bound with the journal cap and document the relationship.

## Verified solid (no action)
- #2 CI proto-drift gate present.
- #3/#4 trade_id round-trip: SPA `setCell` spreads the row (preserves
  trade_id), `COLUMNS` + Excel iterate explicit lists excluding it,
  `putPlan` `DisallowUnknownFields` accepts the optional field.
- #5 `Store.AutoFillJournal`: single tx + `SELECT ... FOR UPDATE` +
  blob-only UPDATE; all paths commit/rollback.
- #6 planned R:R stamped on manual reconciled trades (open + closed).
- #7 tz threaded from `?tz` into the merge.

## Commit steps
  A. tracker (this commit).
  B. cap-hit signal + headroom (metric + log; raise/justify cap).
  C. auto-fill metrics (filled/updated/appended/capped/read_error).
  D. reader closed-set bound aligned with the cap + documented.
  E. flip tracker to DONE.
