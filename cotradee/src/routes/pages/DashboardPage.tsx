import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { X } from 'lucide-react';
import { useExecutionState } from '@/features/execution/api/brokerAccount';
import { useActiveBrokerConnection } from '@/features/broker/api/brokerConnections';
import { useManagedTrades } from '@/features/journal/api/journal';
import {
  TradingChart,
  type ActiveTrade,
} from '@/features/chart/components/TradingChart';
import { useActiveSymbol } from '@/features/chart/hooks/useActiveSymbol';
import { WelcomeSetupCard } from '@/features/tradingsystem/components/WelcomeSetupCard';
import { useOnboardingProgress } from '@/features/tradingsystem/hooks/useOnboardingProgress';
import { useAuth } from '@/features/auth/context/AuthContext';

/**
 * Dashboard.
 *
 * The chart is the main surface. The price levels drawn are:
 *
 *   - `ActiveTrade[]`: live broker position(s) and pending order(s) for 
 *                      the active symbol. Levels persist and update 
 *                      instantly as reported by the broker state.
 *
 * The live-reasoning popup (`AnalysisOverlay`) is NOT rendered here;
 * it lives in `DashboardLayout.tsx` as a single global instance that
 * floats over every authenticated route.
 */

/** Timeframe localStorage key. The symbol selection is owned by
 * useActiveSymbol, which persists to localStorage itself. */
const TF_KEY = 'active_tf';

function normalizeSymbol(s: string | undefined | null): string {
  return (s ?? '').replace(/m$/i, '').toUpperCase();
}

export default function DashboardPage() {
  useAuth();

  const { data: execState } = useExecutionState();
  const { data: managed } = useManagedTrades();

  // Onboarding: fresh users (no broker + no symbols) are auto-redirected
  // to the full-screen /onboarding wizard. Users who "skipped" the wizard
  // (have no broker but landed here intentionally) see the WelcomeSetupCard.
  const broker = useActiveBrokerConnection();
  const onboarding = useOnboardingProgress();
  const navigate = useNavigate();

  const noBroker = !broker.isLoading && !broker.data;

  // Show WelcomeSetupCard for users who skipped onboarding (no broker)
  const needsOnboarding = noBroker;

  // Partially-onboarded: broker connected but not all steps done.
  // Show Resume Setup pill pointing to /onboarding.
  const showResumeSetupPill =
    !needsOnboarding && !onboarding.loading && !onboarding.ready;

  // Chart symbol is owned by the shared useActiveSymbol hook.
  // Resolution order (see hook docstring):
  //   URL ?symbol= -> broker-valid localStorage -> active connection's
  //   mt5_symbol -> first broker-catalog entry -> '' (Select prompt).
  // The hook never falls back to gateway DEFAULT_SYMBOLS, which was the
  // root cause of the chart trying EURUSD on brokers that publish
  // EURUSDm / EURUSD.x.
  const { symbol: activeSymbol, setActiveSymbol } = useActiveSymbol();

  const [searchParams, setSearchParams] = useSearchParams();
  const timeframe =
    searchParams.get('tf') || localStorage.getItem(TF_KEY) || 'H1';

  // One-time mount sync: when the hook has resolved a symbol but the
  // URL does not yet carry ?symbol=, push the value into the URL so
  // WatchlistSidebar / Header and any other URL-readers stay in sync.
  // setActiveSymbol writes URL + localStorage atomically; this guard
  // prevents an infinite loop with the hook's own resolution.
  const didSyncRef = useRef(false);
  useEffect(() => {
    if (didSyncRef.current) return;
    if (!activeSymbol) return;

    const urlHasSymbol = searchParams.has('symbol');
    const urlHasTf = searchParams.has('tf');

    if (!urlHasSymbol || !urlHasTf) {
      didSyncRef.current = true;
      if (!urlHasSymbol) {
        setActiveSymbol(activeSymbol);
      }
      if (!urlHasTf) {
        setSearchParams(
          (prev) => {
            const next = new URLSearchParams(prev);
            next.set('tf', timeframe);
            return next;
          },
          { replace: true },
        );
      }
    } else {
      didSyncRef.current = true;
    }
  }, [activeSymbol, timeframe, searchParams, setSearchParams, setActiveSymbol]);

  // Live broker positions for the active symbol. These are the source
  // of truth while a trade is open (broker may have adjusted SL/TP).
  const activeTrades = useMemo<ActiveTrade[]>(() => {
    const out: ActiveTrade[] = [];
    const activeNorm = normalizeSymbol(activeSymbol);
    if (!activeNorm) return out;

    // 1. Process live open positions
    const positions = execState?.open_positions;
    if (positions) {
      for (const [sym, pos] of Object.entries(positions) as [string, any][]) {
        if (normalizeSymbol(sym) !== activeNorm) continue;
        const entry = Number(pos.price_open);
        if (Number.isNaN(entry)) continue;
        out.push({
          symbol: sym,
          entryPrice: entry,
          stopLoss: pos.sl != null && !Number.isNaN(Number(pos.sl)) ? Number(pos.sl) : 0,
          takeProfit: pos.tp != null && !Number.isNaN(Number(pos.tp)) ? Number(pos.tp) : 0,
          direction: String(pos.direction ?? '').toUpperCase() === 'BUY' ? 'BUY' : 'SELL',
          profit: Number(pos.profit ?? 0),
          isPending: false,
        });
      }
    }

    // 2. Process live pending orders
    const pending = execState?.pending_orders;
    if (pending && Array.isArray(pending)) {
      for (const order of pending) {
        if (normalizeSymbol(order.symbol) !== activeNorm) continue;
        const entry = Number(order.price);
        if (Number.isNaN(entry)) continue;
        out.push({
          symbol: order.symbol,
          entryPrice: entry,
          stopLoss: order.sl != null && !Number.isNaN(Number(order.sl)) ? Number(order.sl) : 0,
          takeProfit: order.tp != null && !Number.isNaN(Number(order.tp)) ? Number(order.tp) : 0,
          direction: String(order.direction ?? '').toUpperCase() === 'BUY' ? 'BUY' : 'SELL',
          profit: 0,
          isPending: true,
        });
      }
    }

    return out;
    // `managed` is intentionally in the dep list so we refresh when the
    // management service reports a close, even if `execState` is stale
    // for a tick.
  }, [execState, managed, activeSymbol]);

  // Broker-sourced symbol metadata (point, digits) for accurate pip
  // calculations. Streamed from the broker, NOT hardcoded.
  const symbolMeta = useMemo(() => {
    return (execState as any)?.symbol_meta ?? {};
  }, [execState]);

  return (
    <div className="flex w-full overflow-hidden animate-fade-in bg-surface-1" style={{ height: 'calc(100dvh - var(--header-height))' }}>
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 relative min-h-0">
          {needsOnboarding ? (
            <WelcomeSetupCard />
          ) : activeSymbol ? (
            <TradingChart
              symbol={activeSymbol}
              timeframe={timeframe}
              activeTrades={activeTrades}
              symbolMeta={symbolMeta}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-content-muted">
              Add a symbol from the watchlist to begin charting.
            </div>
          )}
          {showResumeSetupPill && (
            <DraggableResumePill 
              completed={onboarding.completed} 
              total={onboarding.total} 
              onResume={() => navigate('/onboarding')} 
            />
          )}
        </div>
      </div>
    </div>
  );
}

function DraggableResumePill({ completed, total, onResume }: { completed: number; total: number; onResume: () => void }) {
  const [isDismissed, setIsDismissed] = useState(() => sessionStorage.getItem('exoper_resume_pill_dismissed') === 'true');
  const [position, setPosition] = useState({ x: 0, y: 0 });
  
  const isDragging = useRef(false);
  const startPos = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const handleMove = (e: PointerEvent) => {
      if (!isDragging.current) return;
      e.preventDefault();
      setPosition({
        x: e.clientX - startPos.current.x,
        y: e.clientY - startPos.current.y,
      });
    };

    const handleUp = () => {
      isDragging.current = false;
      document.body.style.userSelect = '';
    };

    window.addEventListener('pointermove', handleMove, { passive: false });
    window.addEventListener('pointerup', handleUp);
    window.addEventListener('pointercancel', handleUp);

    return () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
      window.removeEventListener('pointercancel', handleUp);
    };
  }, []);

  if (isDismissed) return null;

  const handlePointerDown = (e: React.PointerEvent) => {
    // Prevent dragging if they clicked a button
    if ((e.target as HTMLElement).closest('button')) return;
    
    isDragging.current = true;
    startPos.current = { x: e.clientX - position.x, y: e.clientY - position.y };
    document.body.style.userSelect = 'none'; // prevent text selection while dragging
  };

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    sessionStorage.setItem('exoper_resume_pill_dismissed', 'true');
    setIsDismissed(true);
  };

  return (
    <div
      onPointerDown={handlePointerDown}
      style={{ transform: `translate(${position.x}px, ${position.y}px)`, touchAction: 'none' }}
      className="absolute bottom-6 right-6 z-50 flex items-center gap-2 rounded-full border border-border bg-surface pl-4 pr-1.5 py-1.5 text-xs font-semibold text-content shadow-xl cursor-grab active:cursor-grabbing"
    >
      <button 
        type="button" 
        onClick={onResume} 
        className="flex items-center gap-2 hover:opacity-80 transition-opacity"
      >
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-brand" aria-hidden />
        Resume setup
        <span className="text-content-muted tabular-nums">
          {completed}/{total}
        </span>
      </button>
      <div className="w-[1px] h-3 bg-border mx-1" />
      <button 
        type="button" 
        onClick={handleDismiss}
        className="p-1.5 rounded-full hover:bg-black/5 dark:hover:bg-white/5 text-content-muted hover:text-content transition-colors"
        aria-label="Close"
      >
        <X size={14} />
      </button>
    </div>
  );
}
