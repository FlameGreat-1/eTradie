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
  PARTIAL_CLOSE:       [
    ['management', 'trades'],
    ['management', 'journal'],
    ['management', 'metrics'],
    ['execution', 'state'],
    ['execution', 'account'],
  ],
  TRADE_CLOSED:        [
    ['management', 'trades'],
    ['management', 'journal'],
    ['management', 'metrics'],
    ['execution', 'state'],
    ['execution', 'account'],
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
};

/**
 * Apply the canonical invalidation set for a single event. Unknown
 * event types are a no-op (so a backend rollout that adds a new type
 * never breaks the dashboard).
 */
export function applyEventInvalidations(qc: QueryClient, event: RealtimeEvent): void {
  const keys = INVALIDATION_MAP[event.type];
  if (!keys || keys.length === 0) return;
  for (const key of keys) {
    void qc.invalidateQueries({ queryKey: key as unknown[] });
  }
}
