import { useEffect, useRef, useCallback, useState } from 'react';
import { env } from '@/config/env';
import { useAuth } from '@/features/auth';

/**
 * True WebSocket hook for live tick streaming from the engine.
 *
 * Cookie-auth (Batch 11 + cookie-auth-engine-and-services):
 *   The browser attaches the HttpOnly access_token cookie to the WS
 *   handshake automatically. The engine resolves the user from that
 *   cookie before the init frame (src/engine/routers/chart.py,
 *   src/engine/shared/auth.py::verify_token_from_websocket).
 *   Cookies are scoped by host (not port) under RFC 6265, so cookies
 *   set on the gateway host reach the engine host on local-dev
 *   (`localhost:8080` + `localhost:8000`) and on any production
 *   topology where the gateway and engine share a registrable
 *   domain configured via AUTH_COOKIE_DOMAIN. See section 4.4 of
 *   docs/cookie-auth.md for the cross-host constraint.
 *
 * Protocol (server contract now matches; no mismatch):
 *   1. On mount, opens a WebSocket to /api/broker/stream-ticks. The
 *      browser includes the access_token cookie on the handshake.
 *   2. Sends an init frame: { symbol }. No token field is sent;
 *      the engine reads the cookie. Non-browser CLI clients MAY
 *      still send { token, symbol } — the engine accepts both.
 *   3. Receives tick frames: { bid, ask, time, symbol }.
 *   4. When activeSymbol changes, sends a switch frame: { symbol }.
 *   5. On unmount, closes cleanly.
 *
 * Reconnects automatically with exponential backoff on disconnect.
 */
export interface TickData {
  bid: number;
  ask: number;
  time: number;
  symbol: string;
}

interface UseTickStreamOptions {
  /** The symbol to stream ticks for. */
  symbol: string;
  /** Called on every tick frame. */
  onTick?: (tick: TickData) => void;
}

export function useTickStream({ symbol, onTick }: UseTickStreamOptions) {
  const { isAuthenticated } = useAuth();
  const wsRef = useRef<WebSocket | null>(null);
  const symbolRef = useRef(symbol);
  const onTickRef = useRef(onTick);
  const reconnectAttemptsRef = useRef(0);
  const disposedRef = useRef(false);
  const [isConnected, setIsConnected] = useState(false);
  const [lastTick, setLastTick] = useState<TickData | null>(null);

  onTickRef.current = onTick;

  // Send symbol-switch message when symbol changes after initial connection.
  useEffect(() => {
    if (symbolRef.current !== symbol && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ symbol }));
    }
    symbolRef.current = symbol;
  }, [symbol]);

  const connect = useCallback(() => {
    if (disposedRef.current) return;

    if (!symbolRef.current) return;

    // Single public entry point (Option B): the live-tick WebSocket goes
    // to the gateway WS origin, which reverse-proxies the upgrade to the
    // engine's /api/broker/stream-ticks handler. The browser attaches the
    // HttpOnly access_token cookie to the handshake automatically.
    const ws = new WebSocket(`${env.apiWsUrl}/api/broker/stream-ticks`);
    wsRef.current = ws;

    ws.onopen = () => {
      // Send init frame with the initial symbol. The user identity
      // comes from the access_token cookie on the upgrade request,
      // not from the body.
      ws.send(JSON.stringify({ symbol: symbolRef.current }));
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.error) {
          // Transient broker error — server stays connected.
          return;
        }
        const tick: TickData = {
          bid: data.bid,
          ask: data.ask,
          time: data.time,
          symbol: data.symbol,
        };
        setLastTick(tick);
        onTickRef.current?.(tick);
      } catch {
        // Malformed frame — ignore.
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;

      if (disposedRef.current) return;

      // Reconnect with exponential backoff, capped at 30s.
      reconnectAttemptsRef.current = Math.min(reconnectAttemptsRef.current + 1, 6);
      const delay = Math.min(1000 * 2 ** (reconnectAttemptsRef.current - 1), 30_000);
      setTimeout(() => {
        if (!disposedRef.current) connect();
      }, delay);
    };

    ws.onerror = () => {
      // onerror is always followed by onclose — let onclose handle reconnect.
    };
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    disposedRef.current = false;
    connect();

    return () => {
      disposedRef.current = true;
      if (wsRef.current) {
        const ws = wsRef.current;
        if (ws.readyState === WebSocket.CONNECTING) {
          ws.addEventListener('open', () => ws.close());
        } else {
          ws.close();
        }
        wsRef.current = null;
      }
    };
  }, [isAuthenticated, connect]);

  return { isConnected, lastTick };
}
