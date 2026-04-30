import type { Query } from '@tanstack/react-query';

/**
 * Shared resilient-polling helpers for TanStack Query.
 *
 * Any query that uses `refetchInterval` (periodic polling) should use
 * these helpers so the frontend behaves like TradingView / MetaTrader:
 *
 *   • Zero retries on any polling query — the interval IS the retry
 *   • Exponential back-off on the polling interval while unhealthy
 *   • Instant recovery once the service responds again
 *
 * NOTE: The browser's `GET ... 503` network log line in DevTools is
 * Chrome's built-in behaviour — no JavaScript can suppress it.  Even
 * TradingView, Bloomberg Terminal, and MetaTrader Web show these in
 * the console.  What we control is HOW OFTEN they appear.
 */

/**
 * For polling queries, retries within a single fetch cycle are
 * redundant: the `refetchInterval` already acts as the retry loop.
 * Setting `retry: false` means each poll cycle fires exactly ONE
 * request.  No duplicates.
 */
export const POLL_RETRY = false as const;

/**
 * Returns a `refetchInterval` function that exponentially backs off
 * when the query is in an error state (up to 60 s), then snaps back
 * to `baseMs` the instant the service starts responding again.
 *
 * This means:
 *   • Service healthy → polls every `baseMs` (e.g. 3 s) with zero
 *     added latency.  WebSocket events invalidate the cache for
 *     truly instant updates between polls.
 *   • Service down → 1 request on mount, then backs off:
 *     baseMs → 2× → 4× → 8× → 16× → capped at 60 s.
 *   • Service recovers → the next successful response puts the
 *     query status back to 'success', and the very next interval
 *     fires at the original `baseMs`.
 *
 * Usage:
 * ```ts
 * useQuery({
 *   refetchInterval: adaptiveInterval(3_000),
 *   retry: POLL_RETRY,          // false — no retry within a cycle
 * })
 * ```
 */
export function adaptiveInterval(baseMs: number) {
  return (query: Query<any, any, any, any>): number | false => {
    const { status, dataUpdateCount, errorUpdateCount } = query.state;
    if (status === 'error') {
      const consecutiveErrors = dataUpdateCount === 0 ? errorUpdateCount : 1;
      return Math.min(baseMs * 2 ** Math.min(consecutiveErrors, 4), 60_000);
    }
    return baseMs;
  };
}
