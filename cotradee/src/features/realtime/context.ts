/**
 * Realtime context object.
 *
 * Extracted from RealtimeProvider.tsx so the context identity is
 * STABLE across Vite Fast Refresh / HMR cycles. Files that export
 * React components are re-evaluated on every relevant edit, which
 * was creating a fresh `createContext()` instance each time. The
 * already-mounted provider then held the OLD context while a
 * newly-imported consumer module imported the NEW one, producing
 * the `useRealtime must be used inside <RealtimeProvider>` error
 * even though the provider was visibly in the tree.
 *
 * Keeping the context here — a value-only module with NO component
 * export — means React Fast Refresh does not invalidate it on edits
 * to the provider or the hooks, so the consumer-vs-provider
 * identity check holds end-to-end for the life of the process.
 */
import { createContext } from 'react';
import type { RealtimeEvent } from './types';

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

export const RealtimeContext = createContext<RealtimeContextValue | undefined>(undefined);
