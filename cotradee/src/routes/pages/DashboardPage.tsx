import { useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useExecutionState } from '@/features/execution/api/brokerAccount';
import { useLatestAnalysis } from '@/features/analysis/api/analysis';
import { useSymbols } from '@/features/symbols/api/symbols';
import { useManagedTrades } from '@/features/journal/api/journal';
import {
  TradingChart,
  type TradeLevels,
  type ActiveTrade,
} from '@/features/chart/components/TradingChart';

/**
 * Dashboard.
 *
 * The chart is the main surface. Two kinds of price levels are drawn:
 *
 *   - `TradeLevels`  : planned Entry / SL / TP from the latest VALID
 *                      analysis for the active symbol. Shown as
 *                      persistent price lines while no live position
 *                      exists for that symbol.
 *   - `ActiveTrade[]`: live broker position(s) for the active symbol.
 *                      Replaces the planned projection while the
 *                      trade is open; levels persist until the broker
 *                      reports the position closed.
 *
 * The live-reasoning popup (`AnalysisOverlay`) is NOT rendered here;
 * it lives in `DashboardLayout.tsx` as a single global instance that
 * floats over every authenticated route.
 *
 * Invalid setups ("NO_SETUP", rejected, flat/neutral direction, or
 * proceed_to_module_b === false) are filtered out before being turned
 * into chart levels.
 */

/** localStorage keys — must match Header.tsx */
const SYMBOL_KEY = 'active_symbol';
const TF_KEY = 'active_tf';

const INVALID_DIRECTIONS = new Set([
  '',
  '-',
  'NONE',
  'NO_SETUP',
  'NO SETUP',
  'INVALID',
  'FLAT',
  'NEUTRAL',
  'REJECTED',
]);

function normalizeSymbol(s: string | undefined | null): string {
  return (s ?? '').replace(/m$/i, '').toUpperCase();
}

function isValidSetup(a: any): boolean {
  if (!a) return false;
  if (a.proceed_to_module_b === false) return false;
  const direction = String(a.direction ?? a.raw_output?.direction ?? '')
    .trim()
    .toUpperCase();
  if (INVALID_DIRECTIONS.has(direction)) return false;
  // Must have at least an entry price to be projectable onto the chart.
  const raw = a.raw_output ?? {};
  const entry =
    a.trade_levels?.entry ?? raw.entry_price ?? raw.entry_zone?.low ?? a.entry_price ?? null;
  return entry != null && !Number.isNaN(Number(entry));
}

function extractLevelsFromAnalysis(a: any): TradeLevels | undefined {
  const raw = a.raw_output ?? {};
  const entry = a.trade_levels?.entry ?? raw.entry_price ?? raw.entry_zone?.low ?? a.entry_price;
  const stopLossRaw =
    a.trade_levels?.stop_loss ??
    (typeof raw.stop_loss === 'object' && raw.stop_loss !== null
      ? raw.stop_loss.price
      : raw.stop_loss ?? a.stop_loss);
  const takeProfitRaw =
    a.trade_levels?.take_profit ??
    raw.tp1_price ??
    raw.take_profits?.[0]?.level ??
    raw.take_profit ??
    a.take_profit;

  if (entry == null) return undefined;
  const parsedEntry = Number(entry);
  if (Number.isNaN(parsedEntry)) return undefined;

  const parsedSl = stopLossRaw != null ? Number(stopLossRaw) : undefined;
  const parsedTp =
    takeProfitRaw != null ? Number(takeProfitRaw) : undefined;

  return {
    entry: parsedEntry,
    stopLoss:
      parsedSl != null && !Number.isNaN(parsedSl) ? parsedSl : undefined,
    takeProfit:
      parsedTp != null && !Number.isNaN(parsedTp) ? parsedTp : undefined,
    direction:
      String(a.direction ?? raw.direction ?? '').toUpperCase() || undefined,
  };
}

export default function DashboardPage() {
  const { data: symbolData } = useSymbols();
  const { data: latest } = useLatestAnalysis(50);
  const { data: execState } = useExecutionState();
  const { data: managed } = useManagedTrades();

  const symbols = symbolData?.symbols ?? [];
  const analyses = latest?.analyses ?? [];

  // Chart state from URL (synced with Header controls).
  // On login redirect the URL has no params, so we fall back to the
  // last-viewed instrument persisted in localStorage — exactly how
  // TradingView restores your chart on every visit.
  const [searchParams, setSearchParams] = useSearchParams();
  const activeSymbol =
    searchParams.get('symbol') || localStorage.getItem(SYMBOL_KEY) || '';
  const timeframe =
    searchParams.get('tf') || localStorage.getItem(TF_KEY) || 'H1';

  // One-time mount sync: push the resolved symbol/tf into the URL so
  // Header, WatchlistSidebar, and any other URL-readers stay in sync.
  const didSyncRef = useRef(false);
  useEffect(() => {
    if (didSyncRef.current) return;

    const urlHasSymbol = searchParams.has('symbol');
    const urlHasTf = searchParams.has('tf');

    if (activeSymbol && (!urlHasSymbol || !urlHasTf)) {
      didSyncRef.current = true;
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (!urlHasSymbol) next.set('symbol', activeSymbol);
        if (!urlHasTf) next.set('tf', timeframe);
        return next;
      }, { replace: true });
    } else {
      didSyncRef.current = true;
    }
  }, [activeSymbol, timeframe, searchParams, setSearchParams]);

  // Fallback for first-time users with nothing in localStorage:
  // once the symbols API resolves, auto-select the first instrument.
  useEffect(() => {
    if (!activeSymbol && symbols.length > 0) {
      const firstSymbol = symbols[0];
      localStorage.setItem(SYMBOL_KEY, firstSymbol);
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set('symbol', firstSymbol);
        return next;
      });
    }
  }, [activeSymbol, symbols, setSearchParams]);

  // Live broker positions for the active symbol. These are the source
  // of truth while a trade is open (broker may have adjusted SL/TP).
  const activeTrades = useMemo<ActiveTrade[]>(() => {
    const out: ActiveTrade[] = [];
    const positions = execState?.open_positions;
    if (!positions) return out;
    const activeNorm = normalizeSymbol(activeSymbol);
    for (const [sym, pos] of Object.entries(positions) as [string, any][]) {
      if (normalizeSymbol(sym) !== activeNorm) continue;
      const entry = Number(pos.price_open);
      if (Number.isNaN(entry)) continue;
      out.push({
        symbol: sym,
        entryPrice: entry,
        // TradingChart draws these via `trade.stopLoss > 0` / `trade.takeProfit > 0`
        // guards, so 0 means "don't render".
        stopLoss: pos.sl != null && !Number.isNaN(Number(pos.sl)) ? Number(pos.sl) : 0,
        takeProfit: pos.tp != null && !Number.isNaN(Number(pos.tp)) ? Number(pos.tp) : 0,
        direction: String(pos.direction ?? '').toUpperCase() === 'BUY' ? 'BUY' : 'SELL',
        profit: Number(pos.profit ?? 0),
      });
    }
    return out;
    // `managed` is intentionally in the dep list so we refresh when the
    // management service reports a close, even if `execState` is stale
    // for a tick.
  }, [execState, managed, activeSymbol]);

  // Planned levels projected from the most recent *valid* analysis for
  // this symbol. When no live position is open, these drive the chart.
  const plannedLevels = useMemo<TradeLevels | undefined>(() => {
    const activeNorm = normalizeSymbol(activeSymbol);
    if (!activeNorm) return undefined;
    const match = analyses.find((a: any) => {
      const pairNorm = normalizeSymbol(a.pair ?? a.symbol);
      return pairNorm === activeNorm && isValidSetup(a);
    });
    return match ? extractLevelsFromAnalysis(match) : undefined;
  }, [analyses, activeSymbol]);

  // If a position is open, the live broker levels (via `activeTrades`)
  // already cover Entry/SL/TP for that trade. Skip the planned-levels
  // overlay in that case so the chart doesn't show duplicate markers.
  const levelsForChart = activeTrades.length > 0 ? undefined : plannedLevels;

  return (
    <div className="flex h-full w-full overflow-hidden animate-fade-in bg-surface-1">
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 relative min-h-0">
          {activeSymbol ? (
            <TradingChart
              symbol={activeSymbol}
              timeframe={timeframe}
              levels={levelsForChart}
              activeTrades={activeTrades}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-content-muted">
              Add a symbol from the watchlist to begin charting.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
