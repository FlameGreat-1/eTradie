import { useEffect, useRef, useCallback, useState } from 'react';
import { env } from '@/config/env';

export interface WsEvent {
  type: string;
  source: string;
  severity: string;
  message: string;
  symbol?: string;
  details?: Record<string, unknown>;
  timestamp: string;
  user_id?: string;
}

/**
 * Legacy notifications WebSocket hook.
 *
 * The canonical real-time client is useNotificationsSocket in
 * features/realtime. This file is preserved for any caller that still
 * wires alerts.useWebSocket directly.
 *
 * Cookie-auth (Batch 11 / fix/cookie-auth-finalize-frontend):
 *   The browser attaches the HttpOnly access_token cookie to the WS
 *   handshake automatically. Cookies are scoped by host, not port,
 *   so the cookie set on the gateway host rides along on a Vite
 *   dev-server cross-origin handshake too. The gateway middleware
 *   reads the cookie when no Sec-WebSocket-Protocol token is present.
 *   The SPA never sees the token and cannot forward it (HttpOnly).
 */
export function useWebSocket(onEvent: (event: WsEvent) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);
  const callbackRef = useRef(onEvent);
  callbackRef.current = onEvent;

  const connect = useCallback(() => {
    const url = `${env.gatewayWsUrl}/ws/notifications`;
    const ws = new WebSocket(url);

    ws.onopen = () => {
      reconnectCountRef.current = 0;
      setIsConnected(true);
    };

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as WsEvent;
        callbackRef.current(event);
      } catch { /* ignore malformed frames */ }
    };

    ws.onclose = (e) => {
      setIsConnected(false);
      if (!e.wasClean && reconnectCountRef.current < 10) {
        reconnectCountRef.current++;
        const delay = Math.min(2000 * Math.pow(2, reconnectCountRef.current - 1), 30_000);
        setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close(1000, 'component unmount');
    };
  }, [connect]);

  return { isConnected };
}
