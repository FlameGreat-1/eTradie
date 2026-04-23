import { useEffect, useReducer, useRef } from 'react';
import { getAccessToken } from '@/lib/axios';
import { env } from '@/config/env';
import { useAuth } from '@/features/auth';

/**
 * Live-reasoning stream hook.
 *
 * Opens an SSE connection to `${env.engineUrl}/api/analysis/stream-live`
 * using the canonical Bearer token from localStorage. The endpoint is
 * user-scoped on the server (see engine.processor.streaming), so this
 * hook never observes frames from another user's cycle.
 *
 * Contract matching the engine's publish format:
 *   { type: 'status',           message: string, symbol?: string }
 *   { type: 'reasoning_chunk',  text: string,    symbol?: string }
 *   { type: 'final',            message?: string, symbol?: string }
 *   { type: 'error',            message: string, symbol?: string }
 *
 * Terminal frames (`final`, `error`) close the stream and invoke
 * `onComplete`, which the caller typically uses to refetch the
 * analysis feed.
 */
export interface LiveStreamState {
  /** true while at least one status/reasoning_chunk frame has been seen and no terminal frame yet. */
  isStreaming: boolean;
  /** Current symbol as reported by the latest server frame. */
  symbol: string | null;
  /** Short status line shown above the reasoning block. */
  status: string;
  /** Progressively accumulated reasoning text. */
  reasoning: string;
  /** Error message if the server emitted `type: error`. Cleared on reconnect. */
  error: string | null;
}

type ServerFrame =
  | { type: 'status'; message: string; symbol?: string }
  | { type: 'reasoning_chunk'; text: string; symbol?: string }
  | { type: 'final'; message?: string; symbol?: string }
  | { type: 'error'; message: string; symbol?: string };

type Action =
  | { kind: 'reset' }
  | { kind: 'frame'; frame: ServerFrame };

const INITIAL_STATE: LiveStreamState = {
  isStreaming: false,
  symbol: null,
  status: '',
  reasoning: '',
  error: null,
};

function reducer(state: LiveStreamState, action: Action): LiveStreamState {
  if (action.kind === 'reset') return INITIAL_STATE;

  const { frame } = action;
  const symbol = frame.symbol ?? state.symbol;

  switch (frame.type) {
    case 'status':
      return { ...state, isStreaming: true, symbol, status: frame.message, error: null };
    case 'reasoning_chunk':
      return {
        ...state,
        isStreaming: true,
        symbol,
        reasoning: state.reasoning + frame.text,
        status: 'Analyzing...',
        error: null,
      };
    case 'final':
      // Keep the final reasoning on screen briefly; caller decides when to reset.
      return { ...state, isStreaming: false, status: 'NEW SETUP', error: null };
    case 'error':
      return { ...state, isStreaming: false, status: 'Error', error: frame.message };
    default:
      return state;
  }
}

/**
 * Parse a batch of SSE text containing 0..N events. Returns parsed
 * frames in order. Comment frames (`: keepalive`) are silently
 * discarded. Malformed JSON in a `data:` line is discarded with no
 * side effects: the stream contract is "valid frames only" but we
 * stay resilient to a flaky transport.
 */
function parseSSEBatch(raw: string): ServerFrame[] {
  const frames: ServerFrame[] = [];
  for (const block of raw.split('\n\n')) {
    const line = block.trim();
    if (!line || line.startsWith(':')) continue;
    if (!line.startsWith('data:')) continue;
    const payload = line.slice(5).trim();
    if (!payload) continue;
    try {
      const parsed = JSON.parse(payload) as ServerFrame;
      if (parsed && typeof parsed.type === 'string') {
        frames.push(parsed);
      }
    } catch {
      /* swallow: bad frame on the wire is not fatal. */
    }
  }
  return frames;
}

export function useLiveReasoningStream(onComplete?: () => void): LiveStreamState {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const { isAuthenticated } = useAuth();
  const controllerRef = useRef<AbortController | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    if (!isAuthenticated) return;

    let disposed = false;

    const connect = async () => {
      const token = getAccessToken();
      if (!token) return;

      const controller = new AbortController();
      controllerRef.current = controller;

      try {
        const res = await fetch(`${env.engineUrl}/api/analysis/stream-live`, {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'text/event-stream',
          },
          signal: controller.signal,
          credentials: 'omit',
        });

        if (!res.ok || !res.body) {
          // 401/403/5xx -> let the outer retry handle it, but don't hammer.
          throw new Error(`stream handshake failed: ${res.status}`);
        }

        // Reset retry counter once we've successfully handshaked so a
        // later mid-stream disconnect retries from a short delay
        // rather than a long one.
        reconnectAttemptsRef.current = 0;

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (!disposed) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          // SSE frames are separated by \n\n. Keep the trailing partial
          // (if any) in the buffer for the next iteration.
          const lastBoundary = buffer.lastIndexOf('\n\n');
          if (lastBoundary === -1) continue;
          const batch = buffer.slice(0, lastBoundary + 2);
          buffer = buffer.slice(lastBoundary + 2);

          for (const frame of parseSSEBatch(batch)) {
            dispatch({ kind: 'frame', frame });
            if (frame.type === 'final' || frame.type === 'error') {
              onCompleteRef.current?.();
              // Reset after a short display hold so the dashboard can
              // briefly show the terminal state before clearing.
              window.setTimeout(() => dispatch({ kind: 'reset' }), 2000);
              controller.abort();
              return;
            }
          }
        }
      } catch (err) {
        if (disposed) return;
        if ((err as Error).name === 'AbortError') return;
        // Reconnect with exponential backoff, capped at 30s.
        reconnectAttemptsRef.current = Math.min(reconnectAttemptsRef.current + 1, 6);
        const delay = Math.min(1000 * 2 ** (reconnectAttemptsRef.current - 1), 30_000);
        window.setTimeout(() => {
          if (!disposed) void connect();
        }, delay);
      }
    };

    void connect();

    return () => {
      disposed = true;
      controllerRef.current?.abort();
      controllerRef.current = null;
    };
  }, [isAuthenticated]);

  return state;
}
