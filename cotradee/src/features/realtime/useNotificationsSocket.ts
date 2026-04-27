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
 *   • Probes the gateway with a tiny HTTP HEAD/GET against /health
 *     BEFORE opening the socket. The browser logs
 *     "WebSocket connection failed" directly to the console (it is
 *     not catchable from JS), so the only way to silence the noise
 *     when the gateway is down is to not call new WebSocket() at all.
 *     If the probe fails the hook waits 60 s before trying again.
 *   • Reconnect uses exponential backoff capped at 30 s when the
 *     gateway is reachable; switches to 60 s heartbeat when it is
 *     not.
 *   • Closes cleanly on logout / unmount.
 */
interface UseNotificationsSocketOptions {
  onEvent: (event: RealtimeEvent) => void;
}

interface SocketStatus {
  isConnected: boolean;
}

const PROBE_TIMEOUT_MS = 2_500;
const SLOW_RETRY_MS = 60_000;
const FAST_RETRY_MAX_MS = 30_000;

/** Convert ws:// or wss:// origin to http(s):// for the health probe. */
function toHttpOrigin(wsUrl: string): string {
  if (wsUrl.startsWith('wss://')) return 'https://' + wsUrl.slice('wss://'.length);
  if (wsUrl.startsWith('ws://')) return 'http://' + wsUrl.slice('ws://'.length);
  return wsUrl;
}

async function probeGatewayReachable(): Promise<boolean> {
  const url = `${toHttpOrigin(env.gatewayWsUrl)}/health`;
  // AbortController so the probe doesn't hang on an unresponsive port.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    // `mode: 'cors'` is necessary because the dev server runs on a
    // different port; the gateway responds with permissive CORS for
    // /health. We don't read the body — only that the request
    // resolves.
    const res = await fetch(url, {
      method: 'GET',
      mode: 'cors',
      cache: 'no-store',
      credentials: 'omit',
      signal: controller.signal,
    });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
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
    let fastFailures = 0;
    let everConnected = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const schedule = (delay: number) => {
      if (disposed) return;
      timer = setTimeout(connect, delay);
    };

    const fastBackoff = () =>
      Math.min(1000 * 2 ** Math.min(fastFailures, 5), FAST_RETRY_MAX_MS);

    const connect = async () => {
      if (disposed) return;

      const token = getAccessToken();
      if (!token) {
        schedule(SLOW_RETRY_MS);
        return;
      }

      // 1. Probe HTTP /health. If the gateway is unreachable we don't
      //    even attempt the WebSocket — the browser logs the failure
      //    of new WebSocket() to the console and we cannot suppress
      //    that.
      const reachable = await probeGatewayReachable();
      if (disposed) return;
      if (!reachable) {
        fastFailures += 1;
        // 60 s heartbeat once the gateway has been confirmed offline.
        schedule(SLOW_RETRY_MS);
        return;
      }

      // 2. Probe succeeded — attempt the actual WebSocket handshake.
      const url = `${env.gatewayWsUrl}/ws/notifications`;
      try {
        ws = new WebSocket(url, ['Bearer', token]);
      } catch {
        fastFailures += 1;
        schedule(everConnected ? fastBackoff() : SLOW_RETRY_MS);
        return;
      }

      ws.onopen = () => {
        if (disposed) return;
        fastFailures = 0;
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

      ws.onerror = () => { /* close handler does the work */ };

      ws.onclose = () => {
        if (!disposed) setIsConnected(false);
        ws = null;
        if (disposed) return;
        if (everConnected) {
          fastFailures = 0;
          schedule(1000);
        } else {
          fastFailures += 1;
          schedule(everConnected ? fastBackoff() : SLOW_RETRY_MS);
        }
      };
    };

    void connect();

    return () => {
      disposed = true;
      if (timer) clearTimeout(timer);
      if (ws) {
        try {
          ws.close(1000, 'unmount');
        } catch {
          /* ignore */
        }
      }
    };
  }, [isAuthenticated]);

  return { isConnected };
}
