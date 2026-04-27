import { useEffect, useRef, useState } from 'react';
import { getAccessToken } from '@/lib/axios';
import { env } from '@/config/env';
import { useAuth } from '@/features/auth';
import type { RealtimeEvent } from './types';

/**
 * Single shared connection to ${gatewayWsUrl}/ws/notifications.
 *
 * Behaviour:
 *   • Opens only when the user is authenticated.
 *   • Sends auth via the WebSocket subprotocol header (Bearer, token);
 *     the gateway middleware extracts and validates it from
 *     `Sec-WebSocket-Protocol` (see src/auth/middleware.go).
 *   • Reconnects with exponential backoff capped at 30s. After 6 failed
 *     attempts in a row WITHOUT ever seeing onopen, the hook switches
 *     to a slow 60s heartbeat retry so a missing gateway service does
 *     not flood the dev console with reconnect noise.
 *   • Closes cleanly on logout / unmount.
 */
interface UseNotificationsSocketOptions {
  onEvent: (event: RealtimeEvent) => void;
}

interface SocketStatus {
  isConnected: boolean;
}

const MAX_FAST_RETRIES = 6;
const SLOW_RETRY_MS = 60_000;

export function useNotificationsSocket({ onEvent }: UseNotificationsSocketOptions): SocketStatus {
  const { isAuthenticated } = useAuth();
  const callbackRef = useRef(onEvent);
  callbackRef.current = onEvent;

  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      setIsConnected(false);
      return;
    }

    let disposed = false;
    let ws: WebSocket | null = null;
    let reconnectAttempts = 0;
    let everConnected = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const scheduleReconnect = () => {
      if (disposed) return;
      reconnectAttempts += 1;
      const delay =
        reconnectAttempts > MAX_FAST_RETRIES && !everConnected
          ? SLOW_RETRY_MS
          : Math.min(1000 * 2 ** Math.min(reconnectAttempts - 1, 5), 30_000);
      reconnectTimer = setTimeout(connect, delay);
    };

    const connect = () => {
      if (disposed) return;
      const token = getAccessToken();
      if (!token) {
        scheduleReconnect();
        return;
      }

      const url = `${env.gatewayWsUrl}/ws/notifications`;
      try {
        ws = new WebSocket(url, ['Bearer', token]);
      } catch {
        scheduleReconnect();
        return;
      }

      ws.onopen = () => {
        if (disposed) return;
        reconnectAttempts = 0;
        everConnected = true;
        setIsConnected(true);
      };

      ws.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data) as RealtimeEvent;
          if (event && typeof event.type === 'string') {
            callbackRef.current(event);
          }
        } catch {
          /* malformed frame — ignore */
        }
      };

      // Silently swallow onerror; onclose runs right after with the
      // useful information and triggers reconnect logic.
      ws.onerror = () => { /* no-op */ };

      ws.onclose = () => {
        if (!disposed) setIsConnected(false);
        ws = null;
        if (!disposed) scheduleReconnect();
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) {
        try {
          ws.close(1000, 'unmount');
        } catch {
          /* ignore */
        }
      }
      // Don't call setIsConnected here — the component is unmounting,
      // React will GC its state and a setState call from cleanup
      // produces a warning under StrictMode.
    };
  }, [isAuthenticated]);

  return { isConnected };
}
