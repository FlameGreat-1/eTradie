import { useEffect, useRef, useCallback, useState } from 'react';
import { getAccessToken } from '@/lib/axios';
import { env } from '@/config/env';
import { useAuth } from '@/features/auth';

/**
 * True WebSocket hook for live tick streaming from the engine.
 *
 * Protocol:
 *   1. On mount, opens a WebSocket to /api/broker/stream-ticks
 *   2. Sends an init frame: { token, symbol }
 *   3. Receives tick frames: { bid, ask, time, symbol }
 *   4. When activeSymbol changes, sends a switch frame: { symbol }
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

    const token = getAccessToken();
    if (!token || !symbolRef.current) return;

    // Derive WebSocket URL from the engine HTTP URL.
    const wsBase = env.engineUrl.replace(/^http/, 'ws');
    const ws = new WebSocket(`${wsBase}/api/broker/stream-ticks`);
    wsRef.current = ws;

    ws.onopen = () => {
      // Send init frame with auth token and initial symbol.
      ws.send(JSON.stringify({ token, symbol: symbolRef.current }));
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
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [isAuthenticated, connect]);

  return { isConnected, lastTick };
}
