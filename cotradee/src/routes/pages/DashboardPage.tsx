import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useExecutionState } from '@/features/execution/api/brokerAccount';
import { useLatestAnalysis } from '@/features/analysis/api/analysis';
import { useSymbols } from '@/features/symbols/api/symbols';
import { useManagedTrades } from '@/features/journal/api/journal';
import { useLiveReasoningStream } from '@/features/alerts/hooks/useLiveReasoningStream';
import {
  TradingChart,
  type TradeLevels,
  type ActiveTrade,
} from '@/features/chart/components/TradingChart';
import { AnalysisOverlay } from '@/features/chart/components/AnalysisOverlay';

/**
 * Dashboard.
 *
 * The chart is the main surface; everything else is layered on top:
 *
 *   - `TradeLevels`  : planned Entry / SL / TP from the latest VALID
 *                      analysis for the active symbol. Shown as
 *                      persistent price lines.
 *   - `ActiveTrade[]`: live broker position(s) for the active symbol.
 *                      Overrides the planned projection while the
 *                      trade is open; levels persist until the broker
 *                      reports the position closed.
 *   - `AnalysisOverlay`: live-reasoning popup. Streams tokens as the
 *                      engine emits them, then holds the text on
 *                      screen after `final` until the user dismisses
 *                      or a new cycle for a different symbol arrives.
 *
 * Invalid setups ("NO_SETUP", rejected, flat/neutral direction, or
 * proceed_to_module_b === false) are filtered out before being turned
 * into chart levels.
 */

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
    raw.entry_price ?? raw.entry_zone?.low ?? a.entry_price ?? null;
  return entry != null && !Number.isNaN(Number(entry));
}

function extractLevelsFromAnalysis(a: any): TradeLevels | undefined {
  const raw = a.raw_output ?? {};
  const entry = raw.entry_price ?? raw.entry_zone?.low ?? a.entry_price;
  const stopLossRaw =
    typeof raw.stop_loss === 'object' && raw.stop_loss !== null
      ? raw.stop_loss.price
      : raw.stop_loss ?? a.stop_loss;
  const takeProfitRaw =
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
  const { data: latest, refetch: refetchLatest } = useLatestAnalysis(50);
  const { data: execState } = useExecutionState();
  const { data: managed } = useManagedTrades();

  const symbols = symbolData?.symbols ?? [];
  const analyses = latest?.analyses ?? [];

  // Chart state from URL (synced with Header controls).
  const [searchParams, setSearchParams] = useSearchParams();
  const activeSymbol = searchParams.get('symbol') || '';
  const timeframe = searchParams.get('tf') || 'H1';

  // Whether the reasoning overlay is currently visible. Users can
  // dismiss it; a fresh status frame will re-open it automatically.
  const [overlayOpen, setOverlayOpen] = useState(true);

  // Live reasoning stream. On terminal frames we refetch the feed so
  // the new analysis is available to drive chart levels.
  const stream = useLiveReasoningStream(() => {
    void refetchLatest();
  });

  // Re-open the overlay whenever a new stream actually starts. This
  // lets the user X-out one setup and still see the next one arrive.
  useEffect(() => {
    if (stream.isStreaming) setOverlayOpen(true);
  }, [stream.isStreaming, stream.symbol]);

  // Set initial chart symbol from the user's symbol list if none is selected.
  useEffect(() => {
    if (!activeSymbol && symbols.length > 0) {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set('symbol', symbols[0]);
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
        // TradingChart treats 0 as "don't draw" via `> 0` guards.
        stopLoss: pos.sl != null && !Number.isNaN(Number(pos.sl)) ? Number(pos.sl) : 0,
        takeProfit: pos.tp != null && !Number.isNaN(Number(pos.tp)) ? Number(pos.tp) : 0,
        direction: pos.type === 0 ? 'BUY' : 'SELL',
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

  // If a position is open, prefer the live broker levels; the planned
  // TradeLevels stay as a faint backdrop via `activeTrades` already.
  // We only pass `plannedLevels` when there is no open trade so the
  // chart doesn't duplicate markers.
  const levelsForChart = activeTrades.length > 0 ? undefined : plannedLevels;

  const hasAnyOverlayState =
    stream.isStreaming ||
    !!stream.reasoning ||
    !!stream.error ||
    !!stream.status;

  return (
    <div className="flex h-full w-full overflow-hidden animate-fade-in bg-surface-1">
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 relative min-h-0">
          {activeSymbol ? (
            <>
              <TradingChart
                symbol={activeSymbol}
                timeframe={timeframe}
                levels={levelsForChart}
                activeTrades={activeTrades}
              />
              {overlayOpen && hasAnyOverlayState && (
                <AnalysisOverlay
                  stream={stream}
                  onDismiss={() => {
                    setOverlayOpen(false);
                    stream.reset();
                  }}
                />
              )}
            </>
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
