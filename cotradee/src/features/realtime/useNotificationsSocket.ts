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
 *   • Sends auth via the WebSocket subprotocol header (Bearer, token).
 *     This is what the gateway middleware accepts (auth.RequireAuth
 *     in src/gateway/internal/server/http_server.go).
 *   • Reconnects with exponential backoff capped at 30s on any drop.
 *   • Closes cleanly on logout / unmount.
 *
 * The hook keeps a callback ref so subscribers can change their
 * onEvent handler between renders without tearing down the socket.
 */
interface UseNotificationsSocketOptions {
  onEvent: (event: RealtimeEvent) => void;
}

interface SocketStatus {
  isConnected: boolean;
}

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
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

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

      ws.onerror = () => {
        /* the close handler runs after onerror; let it deal with retry */
      };

      ws.onclose = () => {
        setIsConnected(false);
        ws = null;
        if (!disposed) scheduleReconnect();
      };
    };

    const scheduleReconnect = () => {
      if (disposed) return;
      reconnectAttempts = Math.min(reconnectAttempts + 1, 6);
      const delay = Math.min(1000 * 2 ** (reconnectAttempts - 1), 30_000);
      reconnectTimer = setTimeout(connect, delay);
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
      setIsConnected(false);
    };
  }, [isAuthenticated]);

  return { isConnected };
}
