# Journal: Live Updates + Rolling 90-Day Window (remove 200 cap)

**Status:** IN PROGRESS. Closes the two agreed gaps that remain after
the round-2 hardening, built on `fix/journal-autofill-round2`.

## L1 — Live update (no manual browser refresh)

The whole dashboard auto-updates via ONE WebSocket
(`useNotificationsSocket`) feeding `RealtimeProvider`, which calls
`applyEventInvalidations(qc, event)` -> `eventMap.ts` maps each backend
event type to the React Query key prefixes to invalidate, so the
affected screens refetch with no refresh.

The trading-plan journal is the ONLY surface not on this rail:
`TRADE_SYNCED`, `TRADE_CLOSED`, `PARTIAL_CLOSE` invalidate
`['management', ...]` but never `['trading-plan']`. So a manual trade
only appears after a manual page reload.

**Fix:** add `['trading-plan']` to those three events in `eventMap.ts`.
The plan GET re-runs the auto-fill, so the row appears within ~1s on the
same rail as every other surface. No new socket, no polling.

## W1 — Rolling 90-day window (remove the hard 200 cap)

Agreed design: keep logging forever via a rolling window, NOT a fixed
row cap. The permanent, unbounded record already lives in
`management_trades`. The plan blob holds the CURRENT 90-day window of
auto-filled rows; older AUTO rows the trader never annotated roll OUT
of the blob (objective facts remain in `management_trades`, reachable
by paging the window back); any row the trader annotated (a subjective
cell is non-empty) is ALWAYS kept so no human work is lost.

The merge becomes window-bounded (open date within now-90d) rather than
count-bounded; `journalMaxRows` stops being a silent stop for auto
trades.

## Steps
  [x] A. tracker.
  [x] B. L1 realtime wiring in eventMap.ts (['trading-plan'] on
         TRADE_SYNCED / PARTIAL_CLOSE / TRADE_CLOSED).
  [x] C. W1 backend: window-bounded merge + roll-out of stale
         unannotated auto rows; rolled/capped metrics; the hard 200
         stop is gone (window-bounded; journalMaxRows is now only a
         final safety bound).
  [x] D. W1 read/pagination: ManualTradesWindow reader port + adapter
         (over the existing GetManualJournal since/until/limit/offset);
         read-only GET /api/v1/trading-plan/journal/history?window&page
         returning rows + total_closed + has_more.
  [ ] E. W1 frontend: history client fn + hook + page-back affordance
         in the journal view.
  [ ] F. flip tracker to DONE.
