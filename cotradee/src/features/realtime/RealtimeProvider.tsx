import {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useNotificationsSocket } from './useNotificationsSocket';
import { applyEventInvalidations } from './eventMap';
import { RealtimeContext, type RealtimeContextValue } from './context';
import type { RealtimeEvent } from './types';
import { toast } from '@/hooks/useToast';

/**
 * Event types whose UX is owned by a dedicated, globally mounted
 * modal (NOT the generic destructive toast). The Provider:
 *   1. SUPPRESSES the generic toast for these types so the user does
 *      not get a double-notification (toast AND modal).
 *   2. DISPATCHES a window CustomEvent so the modal listener can open
 *      without prop-drilling or a shared store.
 *
 * The CustomEvent name is the canonical hook the modal listens for;
 * any other source of the same event (e.g. the axios interceptor in
 * cotradee/src/lib/axios.ts that catches a 429 with error_code
 * 'llm_quota_exceeded') dispatches the SAME event name so a single
 * modal subscription covers both the WebSocket and the HTTP code
 * paths.
 *
 * Audit ref: ADMIN-QUOTA-10.
 */
const MODAL_DISPATCH_MAP: Record<string, string> = {
  LLM_QUOTA_EXCEEDED:          'open-llm-quota-modal',
  LLM_PROVIDER_QUOTA_EXCEEDED: 'open-llm-provider-quota-modal',
};

/**
 * WARNING/ERROR event types that are OPERATIONAL — caused by backend /
 * infrastructure conditions the end user cannot act on, and whose raw
 * `message` carries internal plumbing (HTTP status codes, engine_http
 * error chains, Python exception text). These must NEVER be toasted to
 * a normal trader.
 *
 * They are NOT dropped: they still drive query invalidations
 * (eventMap.ts) and reach component subscribers + the realtime feed, so
 * an operator/admin surface and the logs retain the full detail. Only
 * the generic destructive toast is suppressed for them.
 */
const OPERATIONAL_SUPPRESSED_TYPES: ReadonlySet<string> = new Set([
  'PROCESSOR_LLM_FAILED',
  'RAG_RETRIEVAL_FAILED',
  'TA_COLLECTION_FAILED',
  'MACRO_COLLECTION_FAILED',
  'EXECUTION_CALL_FAILED',
  'MANAGEMENT_HANDOFF_FAILED',
  'CYCLE_FAILED',
]);

/**
 * Friendly, non-technical copy for the WARNING/ERROR events a normal
 * user SHOULD see and can act on. The toast renders this curated copy
 * instead of the raw event type / raw backend message, so the user is
 * never shown internal error strings.
 *
 * Any WARNING/ERROR type that is neither here nor in
 * OPERATIONAL_SUPPRESSED_TYPES falls back to a generic, non-technical
 * message (see handleEvent) rather than leaking event internals.
 */
const USER_TOAST_COPY: Record<string, { title: string; description: string }> = {
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
  BROKER_DISCONNECTED: {
    title: 'Broker disconnected',
    description: 'We lost the connection to your broker. Reconnecting automatically.',
  },
  GUARD_WARNING: {
    title: 'Trade caution',
    description: 'A setup passed with a caution flag. Review before it executes.',
  },
};

/**
 * Single global realtime broadcaster.
 *
 * Mounts ONE WebSocket to the gateway notifications endpoint for the
 * lifetime of the authenticated session, dispatches every frame to
 * TanStack Query invalidations, and exposes a small subscription API
 * for components that need raw access to the event stream (e.g. a
 * future Notifications panel or in-app toasts).
 *
 * Why a context (not a hook called per-component): a socket-per-hook
 * design opens N connections per dashboard view. By centralising we
 * keep exactly one connection, share the parsed payload, and avoid
 * thundering-herd reconnects when several components mount at once.
 *
 * Module layout: the React context object itself lives in `./context`
 * (a value-only module with no component exports) so its identity is
 * stable under Vite Fast Refresh / HMR. Keeping it here would cause
 * intermittent "useRealtime must be used inside <RealtimeProvider>"
 * errors after edits, because Fast Refresh would re-evaluate this
 * module and create a fresh context instance for new consumers while
 * the already-mounted provider still held the old one.
 */

const LOG_BUFFER_SIZE = 50;

export type { RealtimeContextValue };

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const subscribersRef = useRef<Set<(event: RealtimeEvent) => void>>(new Set());
  const [latestEvent, setLatestEvent] = useState<RealtimeEvent | null>(null);
  const [recentEvents, setRecentEvents] = useState<RealtimeEvent[]>([]);

  const handleEvent = useCallback(
    (event: RealtimeEvent) => {
      // 1. Drive query invalidations for the affected feature areas.
      applyEventInvalidations(qc, event);

      // 2. Update local broadcast state for any UI subscribers.
      setLatestEvent(event);
      setRecentEvents((prev) => {
        const next = [event, ...prev];
        if (next.length > LOG_BUFFER_SIZE) next.length = LOG_BUFFER_SIZE;
        return next;
      });

      // Modal-owned event types: dispatch the window CustomEvent the
      // globally mounted modal listens for, and suppress the generic
      // toast so the user gets exactly one notification (the modal).
      // Audit ref: ADMIN-QUOTA-10.
      const modalEventName = MODAL_DISPATCH_MAP[event.type as string];
      if (modalEventName) {
        try {
          window.dispatchEvent(
            new CustomEvent(modalEventName, { detail: event }),
          );
        } catch {
          /* SSR or non-DOM env: dispatch is a best-effort optimisation */
        }
      } else if (
        (event.severity === 'WARNING' || event.severity === 'ERROR') &&
        !OPERATIONAL_SUPPRESSED_TYPES.has(event.type as string)
      ) {
        // Curated, user-facing copy only. We NEVER render the raw
        // event.type or the raw backend message to a normal user,
        // because backend failure messages contain internal plumbing
        // (HTTP status, engine_http chains, exception text). Operational
        // backend failures are suppressed above; everything else gets a
        // friendly mapping, with a non-technical generic fallback for
        // any unmapped type so nothing internal ever leaks.
        const copy = USER_TOAST_COPY[event.type as string] ?? {
          title: 'Something needs your attention',
          description: 'Open your dashboard for the latest status.',
        };
        toast({
          title: copy.title,
          description: copy.description,
          variant: 'destructive',
        });
      }

      // 3. Fan out to component subscribers.
      for (const handler of subscribersRef.current) {
        try {
          handler(event);
        } catch {
          /* one bad subscriber should not break the rest */
        }
      }
    },
    [qc],
  );

  const { isConnected } = useNotificationsSocket({ onEvent: handleEvent });

  const subscribe = useCallback((handler: (event: RealtimeEvent) => void) => {
    subscribersRef.current.add(handler);
    return () => {
      subscribersRef.current.delete(handler);
    };
  }, []);

  const value = useMemo<RealtimeContextValue>(
    () => ({ isConnected, latestEvent, recentEvents, subscribe }),
    [isConnected, latestEvent, recentEvents, subscribe],
  );

  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>;
}

export function useRealtime(): RealtimeContextValue {
  const ctx = useContext(RealtimeContext);
  if (!ctx) throw new Error('useRealtime must be used inside <RealtimeProvider>');
  return ctx;
}

/**
 * Subscribe to one or more event types. The handler is kept in a ref
 * so changing it between renders does not re-create the underlying
 * subscription; the subscription itself is set up in `useEffect` so
 * React StrictMode can correctly invoke the cleanup on remount.
 */
export function useRealtimeEvent(
  type: string | string[],
  handler: (event: RealtimeEvent) => void,
) {
  const { subscribe } = useRealtime();
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  const types = Array.isArray(type) ? type : [type];
  const key = types.join('|');

  useEffect(() => {
    if (!key) return;
    const wanted = new Set(types);
    const off = subscribe((event) => {
      if (wanted.has(event.type)) handlerRef.current(event);
    });
    return off;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, subscribe]);
}
