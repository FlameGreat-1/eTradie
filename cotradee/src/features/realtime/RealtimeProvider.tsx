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
      } else if (event.severity === 'WARNING' || event.severity === 'ERROR') {
        // Show generic destructive toast for any other WARNING / ERROR
        // event that does not have a dedicated modal.
        toast({
          title: event.type.replace(/_/g, ' '),
          description: event.message || 'An important event occurred.',
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
