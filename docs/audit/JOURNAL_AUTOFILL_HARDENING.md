# Journal Auto-Fill Hardening (post-merge audit fixes)

**Status:** DONE. All 8 findings from the end-to-end audit of the
manual-trade Daily Execution Journal auto-populate are fixed on branch
`fix/journal-autofill-hardening`.

Scope reminder (unchanged): the EXISTING JournalRow rows are auto-filled
in place from the trader's MANUAL/RECONCILED trades only. No new table,
columns, rows, endpoints or annotations model. The trader still fills
the subjective cells and can hand-type rows for off-system accounts.

## Findings & status

- [x] **#1 proto-gen** — regenerated `management.pb.go` +
      `management_grpc.pb.go`; `GetManualJournal` request/response/entry
      types and the client+server method now exist. (Done on `main`.)
- [x] **#2 CI proto-drift gate** — added a `proto` job to
      `.github/workflows/ci.yml`: installs pinned protoc + plugins, runs
      `make proto-gen`, fails on a non-empty `git diff -- proto/`.
      `test-go` now `needs: [lint, proto]`.
- [x] **#3 PUT round-trip** — added `trade_id?: string` to the SPA
      `JournalRow` so the hidden anchor survives the edit + save
      round-trip (no 400 under `DisallowUnknownFields`, no dropped
      binding). Still never rendered (table + Excel iterate explicit
      column lists).
- [x] **#4 binding survives edit** — the merge is the authoritative
      writer on every load; `Validate` preserves `TradeID` on the
      struct, and the SPA now echoes it back, so one-trade = one-row
      holds across a manual save (no duplicate rows on open->close).
- [x] **#5 write-on-read concurrency** — replaced the handler
      read-modify-write with `Store.AutoFillJournal`: a single
      transaction, `SELECT plan ... FOR UPDATE` row lock, merge, and
      blob-only UPDATE. Concurrent loads serialise; status/version are
      left untouched (auto-fill is not a user edit).
- [x] **#6 RR Planned** — `buildReconciledTrade` computes
      `plannedRR = |tp - entry| / |entry - sl|` for genuinely-manual
      positions and stamps it on the in-memory Trade + persisted
      record; blank when SL/TP absent (never fabricated).
- [x] **#7 timezone** — `getTradingPlan` forwards the browser IANA tz
      as `?tz`; the gateway parses it (`parseTZ`, invalid -> UTC) and
      threads a `*time.Location` into the merge so the Date cell is
      local.
- [x] **#8 gofmt import order** — `container.go` import grouping fixed
      (and a duplicate-import slip corrected).

## Commit steps
  A. tracker + #8 import order.
  B. frontend JournalRow.trade_id (#3) + tz plumbing prep (#7).
  C. gateway putPlan accepts + preserves trade_id (#3/#4).
  D. transactional row-locked merge+persist in the store + tz (#5/#7).
  E. real planned R:R for manual reconciled trades (#6).
  F. CI proto-drift gate (#2).
  G. flip this doc to DONE.
