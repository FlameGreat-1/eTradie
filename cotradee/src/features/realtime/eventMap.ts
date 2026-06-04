import type { QueryClient } from '@tanstack/react-query';
import type { RealtimeEvent } from './types';

/**
 * Map of event-type -> query keys to invalidate.
 *
 * Keys are *prefixes*: passing `['execution']` invalidates every query
 * whose key starts with `['execution', ...]`. This is intentional so
 * that adding new query keys under an existing prefix automatically
 * gets refreshed by the right events without changes here.
 *
 * The list of event types matches src/alert/event.go on the backend
 * 1:1. If you add a new event type there, add it here too with the
 * smallest set of prefixes that need to be refreshed when it fires.
 */
const INVALIDATION_MAP: Record<string, ReadonlyArray<readonly unknown[]>> = {
  /* ── Execution lifecycle ── */
  ORDER_PLACED:        [['execution']],
  ORDER_FILLED:        [['execution'], ['management', 'trades'], ['management', 'metrics']],
  ORDER_CANCELLED:     [['execution']],
  ORDER_EXPIRED:       [['execution']],
  EXECUTION_REJECTED:  [['execution']],
  EXECUTION_HANDOFF:   [['execution'], ['management', 'trades']],
  TRADE_ROUTED:        [['execution']],
  WATCHER_ARMED:       [['execution']],
  WATCHER_TRIGGERED:   [['execution']],
  DAILY_LIMIT_LOCKED:  [['execution']],
  WEEKLY_PAUSED:       [['execution']],
  SIZING_CALCULATED:   [],
  EXECUTION_ERROR:     [['execution']],
  EXECUTION_MODE_CHANGED: [['execution']],
  SETTINGS_UPDATED:    [['execution', 'settings']],
  EXECUTION_CALL_FAILED: [['execution']],

  /* ── Trade manager lifecycle ── */
  BREAKEVEN_SET:       [['management', 'trades'], ['execution', 'state']],
  TRAILING_SL_MOVED:   [['management', 'trades'], ['execution', 'state']],
  // TRADE_SYNCED fires when the reconciler adopts a manually-opened
  // position. ['trading-plan'] is invalidated so the Daily Execution
  // Journal refetches and the gateway auto-fill surfaces the new
  // manual-trade row live (same rail as every other surface), with no
  // browser refresh. The prefix matches both ['trading-plan','plan']
  // and ['trading-plan','status'].
  TRADE_SYNCED:        [['management', 'trades'], ['execution', 'state'], ['trading-plan']],
  PARTIAL_CLOSE:       [
    ['management', 'trades'],
    ['management', 'journal'],
    ['management', 'metrics'],
    ['execution', 'state'],
    ['execution', 'account'],
    ['trading-plan'],
  ],
  TRADE_CLOSED:        [
    ['management', 'trades'],
    ['management', 'journal'],
    ['management', 'metrics'],
    ['execution', 'state'],
    ['execution', 'account'],
    ['trading-plan'],
  ],
  PERFORMANCE_REPORT:  [['management', 'metrics']],
  MANAGEMENT_HANDOFF_FAILED: [['management', 'trades']],

  /* ── Analysis / cycle ── */
  CYCLE_STARTED:       [['analysis']],
  CYCLE_COMPLETED:     [['analysis']],
  CYCLE_FAILED:        [['analysis']],
  CYCLE_RETRYING:      [['analysis']],
  ANALYSIS_COMPLETE:   [['analysis']],
  GUARD_REJECTED:      [['analysis']],
  GUARD_WARNING:       [['analysis']],

  /* ── Symbols / config ── */
  SYMBOLS_CHANGED:     [['symbols']],
  INTERVAL_CHANGED:    [['gateway', 'config']],

  /* ── Market ── */
  CANDLE_CLOSED:       [], // chart handles its own tick stream
  COT_FLIP:            [],
  MACRO_CALENDAR_UPDATE: [],

  /* ── System ── */
  BROKER_DISCONNECTED: [['execution', 'account']],
  BROKER_RECONNECTED:  [['execution', 'account']],
  SERVICE_STARTED:     [],
  SERVICE_STOPPING:    [],
  TA_COLLECTION_FAILED:    [],
  MACRO_COLLECTION_FAILED: [],
  RAG_RETRIEVAL_FAILED:    [],
  PROCESSOR_LLM_FAILED:    [],

  /* ── Billing / subscription ── */
  /*
   * On any tier or status change we refetch BOTH:
   *   - ['billing'] (the user's subscription row used by every
   *                  Pro-gated feature),
   *   - ['auth', 'me'] (the cached profile carries the tier badge
   *                     on the avatar dropdown).
   * Without these invalidations the dashboard would lag by up to
   * React Query's staleTime (60 s) after a successful payment;
   * with them, the SPA reflects the new tier within ~1 s of the
   * webhook landing on the billing service.
   */
  SUBSCRIPTION_UPGRADED:        [['billing'], ['auth', 'me']],
  SUBSCRIPTION_DOWNGRADED:      [['billing'], ['auth', 'me']],
  SUBSCRIPTION_STATUS_CHANGED:  [['billing'], ['auth', 'me']],
  /*
   * SUBSCRIPTION_REQUIRED fires when a user-facing action is refused
   * because the user's current tier does not cover it (e.g. Free user
   * reaches trade-execution routing). The user's subscription state
   * has not moved on the backend, but we still refetch ['billing']
   * and ['auth', 'me'] so the upgrade modal opens against the freshest
   * authoritative state. Execution-state queries are intentionally
   * NOT invalidated — nothing in execution state actually changed.
   */
  SUBSCRIPTION_REQUIRED:        [['billing'], ['auth', 'me']],

  /* LLM quota (Audit ref: ADMIN-QUOTA-10).
   *
   * LLM_QUOTA_EXCEEDED:
   *   pro_managed / admin on the platform key has exhausted a cap.
   *   The gateway recorded the block in billing_usage's blocked
   *   counters; the next GET /api/v1/billing/usage must reflect the
   *   freshly-incremented number. Refetching both ['billing'] and
   *   ['analysis'] keeps the UsagePanel and the analysis row list in
   *   sync with the server-side state the moment the event lands.
   *
   * LLM_PROVIDER_QUOTA_EXCEEDED:
   *   BYOK users do NOT have a billing_usage row to refetch -- the
   *   platform never debited their account because uses_platform_key
   *   is false. Only the analysis row whose cycle just failed needs
   *   to be picked up.
   */
  LLM_QUOTA_EXCEEDED:           [['billing'], ['analysis']],
  LLM_PROVIDER_QUOTA_EXCEEDED:  [['analysis']],
};

/**
 * Apply the canonical invalidation set for a single event. Unknown
 * event types are a no-op (so a backend rollout that adds a new type
 * never breaks the dashboard).
 */
export function applyEventInvalidations(qc: QueryClient, event: RealtimeEvent): void {
  const keys = INVALIDATION_MAP[event.type];
  if (!keys || keys.length === 0) return;
  
  // TRADE_SYNCED arrives from the monitoring engine mere milliseconds after the trade
  // is inserted into Postgres. We add a 500ms delay before refetching so the DB
  // transaction is guaranteed to be fully settled and visible to the API's auto-fill query.
  // Without this, the API fetches the plan before the new trade is visible, resulting in
  // the table not showing the new trade until the user manually refreshes the page.
  if (event.type === 'TRADE_SYNCED') {
    setTimeout(() => {
      for (const key of keys) {
        void qc.invalidateQueries({ queryKey: key as unknown[] });
      }
    }, 500);
    return;
  }

  for (const key of keys) {
    void qc.invalidateQueries({ queryKey: key as unknown[] });
  }
}
