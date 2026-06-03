# Journal Auto-Fill — Round-2 Audit (post #1-#8 merge)

**Status:** DONE. Second end-to-end audit of the manual-trade Daily
Execution Journal auto-fill; all findings resolved on branch
`fix/journal-autofill-round2`.

## Findings

- **A (reviewed, not a bug)** — `applyObjectiveCells` rewrites the
  objective cells from the management fact on every load, including
  blanking the close cells (Exit/RRAchieved/PnL/Outcome) while the
  trade is open. This is correct: objective cells are system-owned and
  the trader only owns the subjective cells. No change.
- **B (FIXED)** — `mergeManualTrades` now returns `mergeStats`
  including `Capped`; the handler records
  `trading_plan_journal_autofill_rows_total{action="capped"}` and emits
  a WARN (`trading_plan_journal_autofill_capped`) with the dropped
  count + cap when a full journal drops a trade. No longer silent.
- **C (FIXED)** — added `trading_plan_journal_autofill_rows_total`
  {updated|filled|appended|capped} and
  `trading_plan_journal_autofill_total`
  {applied|noop|read_error|persist_error}; the handler records one
  outcome per plan-GET auto-fill and per-action row counts.
- **D (reviewed, not a bug)** — `formatStyle` `lower[:1]` is safe for
  the ASCII trading-style enum. No change.
- **E (FIXED)** — replaced the bare `Limit: 500` magic number with the
  named, documented `manualJournalclosedFetchLimit` constant (= 500,
  deliberately above the ~200 journal cap; newest-first ordering keeps
  the most recent closed trades; no pagination needed because anything
  beyond the cap can never bind to a row).

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
