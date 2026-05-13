import {
  createContext,
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
import type { RealtimeEvent } from './types';
import { toast } from '@/hooks/useToast';

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
 */

const LOG_BUFFER_SIZE = 50;

export interface RealtimeContextValue {
  /** True when the underlying WebSocket is connected. */
  isConnected: boolean;
  /** The most recent event observed, or null. */
  latestEvent: RealtimeEvent | null;
  /** Ring buffer of the most recent events (newest first). */
  recentEvents: RealtimeEvent[];
  /**
   * Subscribe to live events. Returns an unsubscribe function.
   * Callers should memoise the handler with `useCallback`.
   */
  subscribe: (handler: (event: RealtimeEvent) => void) => () => void;
}

const RealtimeContext = createContext<RealtimeContextValue | undefined>(undefined);

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

      // Show toast for critical events (especially the new restriction events)
      if (event.severity === 'WARNING' || event.severity === 'ERROR') {
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
