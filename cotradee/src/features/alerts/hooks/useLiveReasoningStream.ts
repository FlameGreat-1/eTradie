import { useEffect, useReducer, useRef } from 'react';
import { env } from '@/config/env';
import { useAuth } from '@/features/auth';

/**
 * Live-reasoning stream hook.
 *
 * Opens an SSE connection to `${env.engineUrl}/api/analysis/stream-live`.
 *
 * Cookie-auth (Batch 11 + cookie-auth-engine-and-services):
 *   fetch() is called with credentials:'include' so the browser
 *   attaches the HttpOnly access_token cookie. The engine reads the
 *   cookie via `engine.shared.auth.get_current_user` exactly the
 *   way it reads `Authorization: Bearer <token>` from CLI clients.
 *   No Authorization header is sent from the browser — the cookie
 *   IS the auth channel.
 *
 *   Cross-host topology requirement: the cookie has to actually
 *   reach the engine. On a single-host or cross-subdomain
 *   deployment with AUTH_COOKIE_DOMAIN set to the registrable
 *   domain, this is automatic. See docs/cookie-auth.md §4.4 for
 *   the constraint when the gateway and engine live on different
 *   registrable domains.
 *
 * Contract matching the engine's publish format:
 *   { type: 'status',           message: string, symbol?: string }
 *   { type: 'reasoning_chunk',  text: string,    symbol?: string }
 *   { type: 'final',            message?: string, symbol?: string }
 *   { type: 'error',            message: string, symbol?: string }
 *
 * Terminal frames (`final`, `error`) close the stream and invoke
 * `onComplete`, which the caller typically uses to refetch the
 * analysis feed. The accumulated reasoning text is kept in state
 * after `final`; the UI (DashboardLayout) controls when the overlay
 * is dismissed, so the reasoning stays visible until the user X's
 * it.
 */
/**
 * A single row in the Thinking Terminal. Each row represents one
 * hacker-verb phase (SHARDING, DETECTING, etc.) with a rapidly
 * updating sub-step message.
 */
export interface PulseEntry {
  /** Symbol this row belongs to. Concurrent multi-symbol cycles keep
   *  distinct rows so one symbol's phase never overwrites another's. */
  symbol: string;
  /** Hacker-verb category (SHARDING, DETECTING, CLAUDING, …). */
  phase: string;
  /** Current sub-step text that updates in-place. */
  message: string;
  /** Origin component: ta, macro, rag, processor. */
  source: string;
  /** True when this phase has finished processing. */
  completed: boolean;
  /** Monotonic counter for render-key stability. */
  seq: number;
}

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
  /** ID of the analysis (populated when hydrating from DB) so it can be dismissed. */
  analysisId: string | null;
  /** Active Thinking Terminal rows — in-place updated by pulse frames. */
  pulses: PulseEntry[];
}

type ServerFrame =
  | { type: 'status'; message: string; symbol?: string }
  | { type: 'reasoning_chunk'; text: string; symbol?: string }
  | { type: 'final'; message?: string; symbol?: string }
  | { type: 'error'; message: string; symbol?: string }
  | { type: 'pulse'; phase: string; message: string; source: string; completed: boolean; symbol?: string };

type Action =
  | { kind: 'reset' }
  | { kind: 'frame'; frame: ServerFrame }
  | { kind: 'hydrate'; payload: { analysisId: string; symbol: string; reasoning: string; status: string } };

const INITIAL_STATE: LiveStreamState = {
  isStreaming: false,
  symbol: null,
  status: '',
  reasoning: '',
  error: null,
  analysisId: null,
  pulses: [],
};

/** Monotonic sequence counter for PulseEntry render keys. */
let _pulseSeq = 0;

function reducer(state: LiveStreamState, action: Action): LiveStreamState {
  if (action.kind === 'reset') return INITIAL_STATE;
  
  if (action.kind === 'hydrate') {
    return {
      ...state,
      isStreaming: false,
      symbol: action.payload.symbol,
      reasoning: action.payload.reasoning,
      status: action.payload.status,
      error: null,
      analysisId: action.payload.analysisId,
    };
  }

  const { frame } = action;
  const symbol = frame.symbol ?? state.symbol;

  // Handle pulse frames: update existing phase row in-place or append new.
  if (frame.type === 'pulse') {
    const { phase, message, source, completed } = frame;

    // First pulse of a fresh run: the hook may have hydrated stale
    // "Analysis Complete" status/reasoning/analysisId from the last DB
    // analysis. Reset that carried-over state so the terminal starts
    // clean instead of showing the previous cycle's frozen result.
    const startingFresh = !state.isStreaming;
    const basePulses = startingFresh ? [] : state.pulses;

    const pulseSymbol = frame.symbol ?? state.symbol ?? '';
    const existing = basePulses.findIndex(
      (p) => p.symbol === pulseSymbol && p.phase === phase && p.source === source,
    );
    let nextPulses: PulseEntry[];
    if (existing >= 0) {
      // In-place update: swap the sub-step text for this symbol's row.
      nextPulses = basePulses.map((p, i) =>
        i === existing ? { ...p, message, completed } : p,
      );
    } else {
      // New phase row scoped to this symbol.
      nextPulses = [
        ...basePulses,
        { symbol: pulseSymbol, phase, message, source, completed, seq: ++_pulseSeq },
      ];
    }
    return {
      ...state,
      isStreaming: true,
      symbol,
      pulses: nextPulses,
      error: null,
      status: startingFresh ? 'Analyzing\u2026' : state.status,
      reasoning: startingFresh ? '' : state.reasoning,
      analysisId: startingFresh ? null : state.analysisId,
    };
  }

  // A 'status' frame signals the start of a fresh reasoning stream, so
  // we reset the progressively accumulated reasoning text. Pulses are
  // symbol-scoped and owned solely by the pulse branch above; the
  // status/reasoning/final/error cases must NOT clear them or a
  // concurrently-analysed symbol's rows would be erased.
  const isNewReasoning = frame.type === 'status';
  const currentReasoning = isNewReasoning ? '' : state.reasoning;
  const currentAnalysisId = isNewReasoning ? null : state.analysisId;

  switch (frame.type) {
    case 'status':
      return { ...state, isStreaming: true, symbol, status: frame.message, error: null, reasoning: currentReasoning, analysisId: currentAnalysisId };
    case 'reasoning_chunk':
      return {
        ...state,
        isStreaming: true,
        symbol,
        reasoning: currentReasoning + frame.text,
        status: 'Generating AI Strategy...',
        error: null,
        analysisId: currentAnalysisId,
      };
    case 'final':
      // Per-symbol completion marker on a shared per-user channel.
      // Keep the reasoning on screen and the stream alive (other
      // symbols may still be processing); only update the status label.
      // isStreaming stays true until the transport closes or an error
      // frame arrives, so the live indicators keep animating for any
      // still-in-flight symbol.
      return { ...state, symbol, status: 'Analysis Complete', error: null, reasoning: currentReasoning, analysisId: currentAnalysisId };
    case 'error':
      return { ...state, isStreaming: false, symbol, status: 'Error', error: frame.message, reasoning: currentReasoning, analysisId: currentAnalysisId };
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

import { useLatestAnalysis } from '@/features/analysis/api/analysis';

export function useLiveReasoningStream(onComplete?: () => void): LiveStreamState {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const { isAuthenticated } = useAuth();
  const { data: latestAnalyses } = useLatestAnalysis(1);

  // Automatically hydrate the reasoning modal from the database on page load
  // or when an autonomous backend analysis completes, UNLESS the user has dismissed it.
  useEffect(() => {
    // If we're already streaming something live, don't overwrite it with DB state.
    if (state.isStreaming) return;
    // A finished live run leaves isStreaming=false but keeps its pulse
    // rows on screen; never overwrite that with a hydrated DB analysis.
    if (state.pulses.length > 0) return;

    const latest = latestAnalyses?.analyses?.[0];
    if (!latest) return;

    const analysisId = String(latest.analysis_id);

    const dismissedId = localStorage.getItem('dismissed_analysis_id');
    if (dismissedId === analysisId) return;

    // The backend returns reasoning inside `display.reasoning`.
    const reasoning = latest.display?.reasoning;
    if (!reasoning) return;

    // Only hydrate if we haven't already hydrated this exact analysis.
    // (We don't want to continually dispatch if the user is just looking at it).
    if (state.analysisId === analysisId) return;

    dispatch({
      kind: 'hydrate',
      payload: {
        analysisId,
        symbol: latest.pair ?? '—',
        reasoning,
        status: 'Analysis Complete',
      },
    });
  }, [latestAnalyses, state.isStreaming, state.analysisId, state.pulses.length]);

  const controllerRef = useRef<AbortController | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    if (!isAuthenticated) return;

    let disposed = false;

    const connect = async () => {
      const controller = new AbortController();
      controllerRef.current = controller;

      try {
        const res = await fetch(`${env.engineUrl}/api/analysis/stream-live`, {
          method: 'GET',
          headers: {
            Accept: 'text/event-stream',
          },
          signal: controller.signal,
          // Send the access_token cookie. credentials:'include' is the
          // browser flag that makes the cookie ride along on a
          // cross-origin fetch; without it the engine sees an
          // unauthenticated request even though the cookie exists.
          credentials: 'include',
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
              // Close the HTTP side so the server can release its
              // writer. The outer effect will re-open for the next
              // cycle. Do NOT reset state here: the reasoning text
              // must remain on screen until the user dismisses the
              // overlay.
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
