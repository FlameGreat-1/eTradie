import { useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useExecutionState } from '@/features/execution/api/brokerAccount';
import { useLatestAnalysis } from '@/features/analysis/api/analysis';
import { useSymbols } from '@/features/symbols/api/symbols';
import { useManagedTrades } from '@/features/journal/api/journal';
import { TradingChart, type TradeLevels, type ActiveTrade } from '@/features/chart/components/TradingChart';

const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H3', 'H4', 'H6', 'H8', 'H12', 'D1', 'W1'] as const;

export default function DashboardPage() {
  const { data: symbolData } = useSymbols();
  const { data: latest } = useLatestAnalysis(50);
  const { data: execState } = useExecutionState();
  const { data: managed } = useManagedTrades();

  const symbols = symbolData?.symbols ?? [];
  const analyses = latest?.analyses ?? [];

  // Chart state from URL (synced with Header controls)
  const [searchParams, setSearchParams] = useSearchParams();
  const activeSymbol = searchParams.get('symbol') || '';
  const timeframe = searchParams.get('tf') || 'H1';

  // Set initial symbol from user's symbol list if none selected.
  useEffect(() => {
    if (!activeSymbol && symbols.length > 0) {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set('symbol', symbols[0]);
        return next;
      });
    }
  }, [activeSymbol, symbols, setSearchParams]);

  const activeTrades = useMemo<ActiveTrade[]>(() => {
    const all: ActiveTrade[] = [];
    if (execState?.open_positions) {
      Object.entries(execState.open_positions).forEach(([sym, pos]: any) => {
        all.push({
          id: pos.ticket,
          symbol: sym,
          direction: pos.type === 0 ? 'BUY' : 'SELL',
          entryPrice: Number(pos.price_open),
          stopLoss: pos.sl ? Number(pos.sl) : undefined,
          takeProfit: pos.tp ? Number(pos.tp) : undefined,
        });
      });
    }
    return all;
  }, [execState, managed]);

  const tradeLevels = useMemo<TradeLevels | undefined>(() => {
    const normalize = (s: string) => s?.replace(/m$/i, '').toUpperCase() || '';
    const activeAnalysis = analyses.find((a: any) => 
      normalize(a.pair) === normalize(activeSymbol) || 
      normalize(a.symbol) === normalize(activeSymbol)
    );
    if (!activeAnalysis) return undefined;
    
    const raw = activeAnalysis.raw_output ?? {};
    const entry = raw.entry_price ?? raw.entry_zone?.low ?? activeAnalysis.entry_price;
    const stopLoss = typeof raw.stop_loss === 'object' && raw.stop_loss !== null 
      ? raw.stop_loss.price 
      : (raw.stop_loss ?? activeAnalysis.stop_loss);
    const takeProfit = raw.tp1_price ?? raw.take_profits?.[0]?.level ?? raw.take_profit ?? activeAnalysis.take_profit;

    if (entry == null) return undefined;

    const parsedEntry = Number(entry);
    const parsedSl = stopLoss != null ? Number(stopLoss) : undefined;
    const parsedTp = takeProfit != null ? Number(takeProfit) : undefined;

    if (isNaN(parsedEntry)) return undefined;
    
    return {
      entry: parsedEntry,
      stopLoss: Number.isNaN(parsedSl as any) ? undefined : parsedSl,
      takeProfit: Number.isNaN(parsedTp as any) ? undefined : parsedTp,
    };
  }, [analyses, activeSymbol]);

  return (
    <div className="flex h-full w-full overflow-hidden animate-fade-in bg-surface-1">
      {/* Main chart area (now full width without sidebar) */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chart container — fills entire space */}
        <div className="flex-1 relative min-h-0">
          {activeSymbol ? (
            <TradingChart
              symbol={activeSymbol}
              timeframe={timeframe}
              levels={tradeLevels}
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
