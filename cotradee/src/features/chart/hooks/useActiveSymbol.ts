import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  useActiveBrokerConnection,
} from '@/features/broker/api/brokerConnections';
import { useBrokerSymbols } from '@/features/symbols/api/symbols';

/**
 * localStorage key for the user's last-viewed chart symbol. Kept
 * exported because non-React migration code (legacy SymbolStep, the
 * one-shot URL sync in DashboardPage) needs to read the same key.
 */
export const ACTIVE_SYMBOL_STORAGE_KEY = 'active_symbol';

export interface ActiveSymbolState {
  /**
   * Resolved active symbol. Empty string means the UI must show the
   * Select Symbol prompt and NOT render the chart. The chart should
   * never be mounted with an empty symbol.
   */
  symbol: string;

  /**
   * True while either the broker catalogue (useBrokerSymbols) or the
   * active broker connection (useActiveBrokerConnection) is still in
   * flight. UIs should render a stable loading state during this
   * window instead of flickering through partial resolutions.
   */
  isResolving: boolean;

  /**
   * True when the resolved symbol came from a broker-aware source
   * (URL with broker-valid value, broker-valid localStorage, active
   * connection's mt5_symbol, or first catalog entry). Useful for
   * telemetry; the UI itself can ignore it.
   */
  isBrokerAware: boolean;

  /**
   * Atomically writes the chosen symbol to BOTH the URL (?symbol=...)
   * and localStorage. Pass an empty string to clear the selection.
   */
  setActiveSymbol: (next: string) => void;
}

/**
 * useActiveSymbol owns chart symbol resolution end to end. Every
 * surface that renders the chart (Header dropdown, DashboardPage,
 * watchlist) must consume this hook so the resolution rules live in
 * one place.
 *
 * Resolution order:
 *
 *   1. URL ?symbol=<sym>              explicit caller intent.
 *   2. localStorage active_symbol     only if it exists in the broker
 *                                     catalogue. A value persisted
 *                                     under a previous broker
 *                                     connection (different suffix
 *                                     convention, deleted symbol) is
 *                                     dropped.
 *   3. Active connection's mt5_symbol the broker-actual name resolved
 *                                     by the hosted provisioner from
 *                                     GET_ALL_SYMBOLS.
 *   4. First entry in the broker     last-resort default once the
 *      catalogue                     catalogue has loaded.
 *   5. ''                            nothing selected; the UI must
 *                                     show the prompt and not mount
 *                                     the chart.
 *
 * The hook NEVER falls back to the gateway's tracked-symbols list
 * (useSymbols / GET /api/v1/symbols). That list is operator-seeded
 * with DEFAULT_SYMBOLS and is correct for the analysis-cycle
 * scheduler, NOT for the chart, which must speak the broker's exact
 * symbol names.
 */
export function useActiveSymbol(): ActiveSymbolState {
  const [searchParams, setSearchParams] = useSearchParams();

  const brokerSymbolsQuery = useBrokerSymbols();
  const activeConnQuery = useActiveBrokerConnection();

  const isResolving =
    brokerSymbolsQuery.isLoading || activeConnQuery.isLoading;

  const catalogue = useMemo(
    () => brokerSymbolsQuery.data?.symbols ?? [],
    [brokerSymbolsQuery.data],
  );

  const catalogueNames = useMemo(() => {
    const set = new Set<string>();
    for (const entry of catalogue) {
      const name = entry?.name?.trim();
      if (name) {
        set.add(name);
      }
    }
    return set;
  }, [catalogue]);

  const urlSymbol = (searchParams.get('symbol') ?? '').trim();
  const persistedSymbol =
    typeof window === 'undefined'
      ? ''
      : (window.localStorage.getItem(ACTIVE_SYMBOL_STORAGE_KEY) ?? '').trim();

  // The active connection row is fetched from the engine and includes
  // mt5_symbol (server-resolved by the hosted provisioner; empty
  // string when the broker has not yet published any symbol).
  //
  // useActiveBrokerConnection's queryFn returns an untyped axios
  // payload, so TanStack infers .data as `{} | null`. Narrow the row
  // to the single field this hook reads; the field is optional +
  // nullable to match the real API shape (engine writes "" before
  // GET_ALL_SYMBOLS has resolved on a freshly-provisioned hosted
  // connection).
  const activeConnection = activeConnQuery.data as
    | { mt5_symbol?: string | null }
    | null
    | undefined;
  const activeConnectionSymbol =
    activeConnection?.mt5_symbol?.toString().trim() ?? '';

  let resolved = '';
  let brokerAware = false;

  if (urlSymbol) {
    // Caller intent always wins; the chart layer is the right place
    // to surface a broker-mismatch error to the user.
    resolved = urlSymbol;
    brokerAware = catalogueNames.size === 0 || catalogueNames.has(urlSymbol);
  } else if (persistedSymbol && catalogueNames.has(persistedSymbol)) {
    resolved = persistedSymbol;
    brokerAware = true;
  } else if (activeConnectionSymbol) {
    resolved = activeConnectionSymbol;
    brokerAware = true;
  } else if (catalogue.length > 0) {
    resolved = catalogue[0]?.name?.trim() ?? '';
    brokerAware = resolved !== '';
  } else {
    resolved = '';
    brokerAware = false;
  }

  // Clear a stale localStorage value once we know the broker
  // catalogue does not contain it. Without this, a previous broker
  // connection's persisted symbol would keep re-appearing in the
  // dropdown label until the user picks something else.
  const cleanedStaleRef = useRef(false);
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (cleanedStaleRef.current) return;
    if (brokerSymbolsQuery.isLoading) return;
    if (!persistedSymbol) return;
    if (catalogueNames.size === 0) return;
    if (catalogueNames.has(persistedSymbol)) return;

    cleanedStaleRef.current = true;
    window.localStorage.removeItem(ACTIVE_SYMBOL_STORAGE_KEY);
  }, [brokerSymbolsQuery.isLoading, catalogueNames, persistedSymbol]);

  const setActiveSymbol = useCallback(
    (next: string) => {
      const trimmed = (next ?? '').trim();
      if (typeof window !== 'undefined') {
        if (trimmed) {
          window.localStorage.setItem(ACTIVE_SYMBOL_STORAGE_KEY, trimmed);
        } else {
          window.localStorage.removeItem(ACTIVE_SYMBOL_STORAGE_KEY);
        }
      }
      setSearchParams(
        (prev) => {
          const next2 = new URLSearchParams(prev);
          if (trimmed) {
            next2.set('symbol', trimmed);
          } else {
            next2.delete('symbol');
          }
          return next2;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  return {
    symbol: resolved,
    isResolving,
    isBrokerAware: brokerAware,
    setActiveSymbol,
  };
}
