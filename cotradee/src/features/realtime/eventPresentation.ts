/**
 * Shared, user-facing presentation layer for backend realtime events.
 *
 * Backend events (src/alert/event.go) carry a raw `message` that, for
 * failure events, contains internal plumbing: HTTP status codes,
 * `engine_http:` error chains, Python exception text, etc. A normal
 * (non-developer) user must NEVER see that, in ANY surface.
 *
 * This module is the single source of truth for "how an event is shown
 * to an end user". It is consumed by:
 *   - the live toast (RealtimeProvider), and
 *   - the notifications dropdown (NotificationsPanel),
 * so both render identical friendly copy and neither ever prints the
 * raw event type or raw backend message.
 *
 * The raw event detail is intentionally preserved in the backend event
 * store / journal for operators; only the user-facing rendering here is
 * sanitised.
 */

/**
 * Operational/infrastructure failure events. Their raw `message` is
 * developer plumbing and they are not user-actionable. The live toast
 * suppresses them entirely; history surfaces show a clean generic
 * label instead of the raw text.
 */
export const OPERATIONAL_EVENT_TYPES: ReadonlySet<string> = new Set([
  'PROCESSOR_LLM_FAILED',
  'RAG_RETRIEVAL_FAILED',
  'TA_COLLECTION_FAILED',
  'MACRO_COLLECTION_FAILED',
  'EXECUTION_CALL_FAILED',
  'MANAGEMENT_HANDOFF_FAILED',
  'CYCLE_FAILED',
]);

interface PresentedEvent {
  title: string;
  description: string;
  /** True when the event is an operational/infra failure (suppress from toast). */
  isOperational: boolean;
}

/**
 * Curated, non-technical copy keyed by backend event type. Covers the
 * full set a normal user can meaningfully see; anything not listed
 * falls back to a safe generic message so no internal string leaks.
 */
const EVENT_COPY: Record<string, { title: string; description: string }> = {
  /* ── User-actionable warnings / errors ── */
  EXECUTION_REJECTED: {
    title: 'Order not placed',
    description: 'Your broker did not accept the order. No position was opened.',
  },
  ORDER_EXPIRED: {
    title: 'Setup expired',
    description: 'The entry window passed before price reached your zone, so the order was cancelled.',
  },
  DAILY_LIMIT_LOCKED: {
    title: 'Daily loss limit reached',
    description: 'Trading is paused for the rest of the day to protect your account.',
  },
  WEEKLY_PAUSED: {
    title: 'Weekly drawdown limit reached',
    description: 'Trading is paused for the rest of the week to protect your account.',
  },
  EXECUTION_HALTED: {
    title: 'Execution halted',
    description: 'New trades are paused by the kill switch. Analysis keeps running; placement resumes when it is released.',
  },
  BROKER_DISCONNECTED: {
    title: 'Broker disconnected',
    description: 'We lost the connection to your broker. Reconnecting automatically.',
  },
  BROKER_RECONNECTED: {
    title: 'Broker reconnected',
    description: 'The connection to your broker is back. Trading has resumed.',
  },
  GUARD_WARNING: {
    title: 'Trade caution',
    description: 'A setup passed with a caution flag. Review before it executes.',
  },
  GUARD_REJECTED: {
    title: 'Setup skipped',
    description: 'A setup was rejected by the safety rules and will not be traded.',
  },

  /* ── Positive lifecycle (shown in history; INFO so no toast) ── */
  ORDER_PLACED: {
    title: 'Order placed',
    description: 'Your order is live with the broker.',
  },
  ORDER_FILLED: {
    title: 'Order filled',
    description: 'Your order was filled and the position is now open.',
  },
  ORDER_CANCELLED: {
    title: 'Order cancelled',
    description: 'The pending order was cancelled.',
  },
  TRADE_ROUTED: {
    title: 'Trade routed',
    description: 'An approved setup was sent to execution.',
  },
  TRADE_CLOSED: {
    title: 'Trade closed',
    description: 'A position was closed.',
  },
  PARTIAL_CLOSE: {
    title: 'Partial close',
    description: 'Part of a position was closed at a take-profit level.',
  },
  BREAKEVEN_SET: {
    title: 'Stop moved to breakeven',
    description: 'Your stop loss was moved to breakeven to protect the trade.',
  },
  TRAILING_SL_MOVED: {
    title: 'Trailing stop moved',
    description: 'Your trailing stop loss advanced with price.',
  },
  ANALYSIS_COMPLETE: {
    title: 'Analysis complete',
    description: 'A symbol finished analysis.',
  },
  WATCHER_ARMED: {
    title: 'Watching for entry',
    description: 'We are monitoring price for your entry zone.',
  },
};

/**
 * Generic, non-technical fallbacks by severity so an unmapped event
 * type still renders cleanly without exposing the raw type/message.
 */
function genericCopy(severity?: string): { title: string; description: string } {
  const sev = (severity ?? '').toUpperCase();
  if (sev === 'ERROR' || sev === 'CRITICAL' || sev === 'WARNING') {
    return {
      title: 'Something needs your attention',
      description: 'Open your dashboard for the latest status.',
    };
  }
  return {
    title: 'Update',
    description: 'A new event was recorded.',
  };
}

/**
 * Resolve the user-facing copy for an event. Never returns the raw
 * event type or the raw backend message.
 *
 * @param type     backend event type (e.g. 'EXECUTION_REJECTED')
 * @param severity backend severity, used only for the generic fallback
 */
export function presentUserEvent(
  type: string | undefined,
  severity?: string,
): PresentedEvent {
  const t = type ?? '';
  const isOperational = OPERATIONAL_EVENT_TYPES.has(t);
  if (isOperational) {
    // Clean, non-technical label for history surfaces; the raw engine
    // text is never shown to the user.
    return {
      title: 'System notice',
      description: 'A background task could not complete. The system will retry automatically.',
      isOperational: true,
    };
  }
  const copy = EVENT_COPY[t] ?? genericCopy(severity);
  return { ...copy, isOperational: false };
}
