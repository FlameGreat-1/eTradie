/**
 * Type definitions for the gateway notifications WebSocket stream.
 *
 * The wire format mirrors `alert.Event` from src/alert/event.go on the
 * Go side. Event type constants are kept in sync with that file: when
 * a new event type is added on the backend it must also be added here
 * AND in `realtime/eventMap.ts` so it can drive UI invalidations.
 */

export type EventSource = 'GATEWAY' | 'EXECUTION' | 'TRADE_MANAGER' | 'SYSTEM';

export type EventSeverity = 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';

/** All known event types emitted by the backend. Mirrors src/alert/event.go. */
export type EventType =
  /* Execution */
  | 'ORDER_PLACED'
  | 'ORDER_FILLED'
  | 'ORDER_CANCELLED'
  | 'ORDER_EXPIRED'
  | 'EXECUTION_REJECTED'
  | 'WATCHER_ARMED'
  | 'WATCHER_TRIGGERED'
  | 'DAILY_LIMIT_LOCKED'
  | 'WEEKLY_PAUSED'
  | 'EXECUTION_HALTED'
  | 'SIZING_CALCULATED'
  | 'EXECUTION_ERROR'
  | 'EXECUTION_MODE_CHANGED'
  | 'SETTINGS_UPDATED'
  /* Gateway */
  | 'CYCLE_STARTED'
  | 'CYCLE_COMPLETED'
  | 'CYCLE_FAILED'
  | 'CYCLE_RETRYING'
  | 'ANALYSIS_COMPLETE'
  | 'GUARD_REJECTED'
  | 'GUARD_WARNING'
  | 'TA_COLLECTION_FAILED'
  | 'MACRO_COLLECTION_FAILED'
  | 'RAG_RETRIEVAL_FAILED'
  | 'PROCESSOR_LLM_FAILED'
  | 'EXECUTION_CALL_FAILED'
  | 'TRADE_ROUTED'
  | 'EXECUTION_HANDOFF'
  | 'MANAGEMENT_HANDOFF_FAILED'
  | 'INTERVAL_CHANGED'
  | 'SYMBOLS_CHANGED'
  /* Market / TA */
  | 'CANDLE_CLOSED'
  | 'COT_FLIP'
  | 'MACRO_CALENDAR_UPDATE'
  /* Trade manager */
  | 'TRAILING_SL_MOVED'
  | 'PARTIAL_CLOSE'
  | 'BREAKEVEN_SET'
  | 'TRADE_CLOSED'
  | 'PERFORMANCE_REPORT'
  | 'TRADE_SYNCED'
  /* System */
  | 'SERVICE_STARTED'
  | 'SERVICE_STOPPING'
  | 'BROKER_DISCONNECTED'
  | 'BROKER_RECONNECTED'
  /* Billing / subscription */
  | 'SUBSCRIPTION_UPGRADED'
  | 'SUBSCRIPTION_DOWNGRADED'
  | 'SUBSCRIPTION_STATUS_CHANGED'
  /* Tier-gated UX upsell (not a state-change) */
  | 'SUBSCRIPTION_REQUIRED'
  /* Billing / LLM quota (Audit ref: ADMIN-QUOTA-8/10).
   * Two distinct types so the SPA can render two distinct modals:
   *   - LLM_QUOTA_EXCEEDED          fires for pro_managed / admin on
   *                                 the platform key whose monthly /
   *                                 daily cap is exhausted. Drives the
   *                                 platform quota modal.
   *   - LLM_PROVIDER_QUOTA_EXCEEDED fires for ANY BYOK user whose own
   *                                 provider (Anthropic / OpenAI /
   *                                 Gemini / self-hosted) returns a
   *                                 quota or rate-limit error. Drives
   *                                 the BYOK provider modal with the
   *                                 "check your provider dashboard"
   *                                 CTA.
   * String values MUST match src/alert/event.go on the Go side and
   * src/engine/shared/alert_publisher.py on the Python side. */
  | 'LLM_QUOTA_EXCEEDED'
  | 'LLM_PROVIDER_QUOTA_EXCEEDED';

export interface RealtimeEvent {
  id: string;
  source: EventSource;
  type: EventType | string;
  severity: EventSeverity;
  timestamp: string;
  user_id?: string;
  symbol?: string;
  direction?: string;
  message: string;
  trace_id?: string;
  details?: Record<string, unknown>;
}
