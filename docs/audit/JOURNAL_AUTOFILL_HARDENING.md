# Journal Auto-Fill Hardening (post-merge audit fixes)

**Status:** IN PROGRESS. Fixes the 8 findings from the end-to-end audit
of the manual-trade Daily Execution Journal auto-populate.

Scope reminder (unchanged): the EXISTING JournalRow rows are auto-filled
in place from the trader's MANUAL/RECONCILED trades only. No new table,
columns, rows, endpoints or annotations model. The trader still fills
the subjective cells and can hand-type rows for off-system accounts.

## Findings & status

- [x] **#1 proto-gen** — regenerated `management.pb.go` +
      `management_grpc.pb.go`; `GetManualJournal` request/response/entry
      types and the client+server method now exist. (Done on `main`.)
- [ ] **#2 CI proto-drift gate** — CI must run `make proto-gen` and fail
      on a non-empty `git diff`, so the generated code can never drift
      from the `.proto` again.
- [ ] **#3 PUT round-trip** — the frontend `JournalRow` type has no
      `trade_id`; the existing `PUT /api/v1/trading-plan` decodes with
      `DisallowUnknownFields`. An auto-filled plan returned to the SPA
      carries `trade_id`, so the round-trip either 400s (echoed id) or
      drops the binding (stripped id). Add `trade_id` to the SPA type
      and carry it through.
- [ ] **#4 binding survives edit** — guarantee `JournalRow.TradeID`
      survives `Validate` + `putPlan` so one-trade = one-row holds
      across a manual save (otherwise the next open->close auto-fill
      can't find the bound row and appends a duplicate).
- [ ] **#5 write-on-read concurrency** — the GET auto-fill does a blind
      read-modify-write via `UpdatePlanContent` with no locking; two
      concurrent loads (multi-tab) can claim the same blank row or lose
      an update. Replace with a single transactional, row-locked
      merge+persist in the store.
- [ ] **#6 RR Planned** — genuinely-manual reconciled trades are
      imported with `rr_ratio = 0`, so the RR Planned cell never
      auto-fills. Compute a real planned R:R from entry/SL/TP1 at
      reconcile time so the objective cell is populated.
- [ ] **#7 timezone** — Date/Session render in UTC only. Thread the
      user's tz through the plan GET (same `tz` convention as the
      pnl-calendar) so the visible cell is local, never raw UTC.
- [x] **#8 gofmt import order** — `container.go` import grouping fixed.

## Commit steps
  A. tracker + #8 import order.
  B. frontend JournalRow.trade_id (#3) + tz plumbing prep (#7).
  C. gateway putPlan accepts + preserves trade_id (#3/#4).
  D. transactional row-locked merge+persist in the store + tz (#5/#7).
  E. real planned R:R for manual reconciled trades (#6).
  F. CI proto-drift gate (#2).
  G. flip this doc to DONE.
