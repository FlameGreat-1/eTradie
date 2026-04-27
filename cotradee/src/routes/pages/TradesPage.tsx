import { useMemo } from 'react';
import { useManagedTrades, usePerformanceMetrics } from '@/features/journal/api/journal';
import { useExecutionState, useCancelOrder } from '@/features/execution/api/brokerAccount';
import { useRealtime } from '@/features/realtime';
import { formatCurrency, formatPercentage, formatVolume } from '@/utils/formatters';
import {
  X,
  Activity,
  Zap,
  TrendingUp,
  BarChart3,
} from 'lucide-react';

interface ManagedTrade {
  trade_id: string;
  symbol: string;
  direction: string;
  entry_price: number;
  current_price: number;
  stop_loss: number;
  tp1_price: number;
  tp2_price?: number;
  tp3_price?: number;
  total_lot_size: number;
  remaining_lot_size: number;
  unrealized_pnl: number;
  realized_pnl: number;
  trading_style: string;
  status: string;
  breakeven_set: boolean;
  tp1_hit: boolean;
  tp2_hit: boolean;
}

interface PendingOrder {
  order_id: string;
  symbol: string;
  direction?: string;
  price?: number;
  volume?: number;
  sl?: number;
  tp?: number;
  status?: string;
}

export default function TradesPage() {
  const { data: managedRaw } = useManagedTrades();
  const { data: execState } = useExecutionState();
  const { data: dailyMetrics } = usePerformanceMetrics('DAILY');
  const { data: allTimeMetrics } = usePerformanceMetrics();
  const cancelOrder = useCancelOrder();
  const { isConnected } = useRealtime();

  const trades = (managedRaw ?? []) as ManagedTrade[];
  const pending = (execState?.pending_orders ?? []) as PendingOrder[];

  const dailyPnl = dailyMetrics?.total_pnl;
  const winRate = allTimeMetrics?.win_rate;

  const totalUnrealized = useMemo(
    () => trades.reduce((acc, t) => acc + (Number(t.unrealized_pnl) || 0), 0),
    [trades],
  );

  return (
    <div className="p-4 sm:p-6 space-y-6 animate-fade-in">
      {/* Overview Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <MetricCard
          icon={<Activity size={18} />}
          label="Open Positions"
          value={String(execState?.open_position_count ?? 0)}
          accessory={isConnected && trades.length > 0 ? <span className="live-dot" /> : null}
        />
        <MetricCard
          icon={<Zap size={18} />}
          label="Pending Orders"
          value={String(execState?.pending_order_count ?? 0)}
        />
        <MetricCard
          icon={<TrendingUp size={18} />}
          label="Daily P&L"
          value={dailyPnl != null ? formatCurrency(dailyPnl) : '---'}
          valueClass={
            dailyPnl == null ? 'text-content' : dailyPnl >= 0 ? 'text-success' : 'text-danger'
          }
        />
        <MetricCard
          icon={<BarChart3 size={18} />}
          label="Win Rate"
          value={winRate != null ? formatPercentage(winRate) : '---'}
        />
      </div>

      {/* Floating unrealised P&L summary (only when there's something to show). */}
      {trades.length > 0 && (
        <div className="rounded-lg border border-border bg-surface-1 px-4 py-2 flex items-center justify-between">
          <span className="text-xs text-content-muted uppercase tracking-wider">
            Aggregate Unrealised P&L
          </span>
          <span
            className={`text-base font-bold ${
              totalUnrealized >= 0 ? 'text-success' : 'text-danger'
            }`}
          >
            {totalUnrealized >= 0 ? '+' : ''}
            {formatCurrency(totalUnrealized)}
          </span>
        </div>
      )}

      {/* Active Managed Trades */}
      <section aria-labelledby="trades-heading">
        <h2 id="trades-heading" className="text-sm font-semibold text-content mb-3">
          Active Managed Trades
        </h2>

        {/* Desktop: full table */}
        <div className="hidden md:block rounded-xl border border-border bg-surface-1 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 z-10 bg-surface-2">
                <tr className="border-b border-border text-content-muted">
                  <Th>Symbol</Th>
                  <Th>Dir</Th>
                  <Th align="right">Entry</Th>
                  <Th align="right">Current</Th>
                  <Th align="right">SL</Th>
                  <Th align="right">TP1</Th>
                  <Th align="right">Lot</Th>
                  <Th align="right">P&amp;L</Th>
                  <Th align="center">Progress</Th>
                  <Th align="center">Status</Th>
                </tr>
              </thead>
              <tbody>
                {trades.length === 0 && (
                  <tr>
                    <td colSpan={10} className="px-4 py-8 text-center text-content-muted">
                      No active trades
                    </td>
                  </tr>
                )}
                {trades.map((t, i) => (
                  <tr
                    key={t.trade_id}
                    className={`border-b border-border last:border-b-0 hover:bg-surface-2 transition-colors duration-fast
                                ${i % 2 === 1 ? 'bg-surface-2/40' : ''}`}
                  >
                    <Td className="font-bold text-brand">{t.symbol}</Td>
                    <Td>
                      <DirectionPill dir={t.direction} />
                    </Td>
                    <Td align="right">{formatCurrency(Number(t.entry_price))}</Td>
                    <Td align="right">{formatCurrency(Number(t.current_price))}</Td>
                    <Td align="right" className="text-content-muted">
                      {formatCurrency(Number(t.stop_loss))}
                    </Td>
                    <Td align="right" className="text-content-muted">
                      {t.tp1_price > 0 ? formatCurrency(Number(t.tp1_price)) : '—'}
                    </Td>
                    <Td align="right" className="text-content-muted">
                      {formatVolume(Number(t.remaining_lot_size))}
                      <span className="text-content-faint">
                        /{formatVolume(Number(t.total_lot_size))}
                      </span>
                    </Td>
                    <Td
                      align="right"
                      className={`font-medium ${
                        Number(t.unrealized_pnl) >= 0 ? 'text-success' : 'text-danger'
                      }`}
                    >
                      {formatCurrency(Number(t.unrealized_pnl))}
                    </Td>
                    <Td align="center">
                      <ProgressDots
                        be={t.breakeven_set}
                        tp1={t.tp1_hit}
                        tp2={t.tp2_hit}
                      />
                    </Td>
                    <Td align="center">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-brand-soft text-brand">
                        {t.status}
                      </span>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Mobile: card list */}
        <div className="md:hidden space-y-2">
          {trades.length === 0 && (
            <div className="rounded-xl border border-border bg-surface-1 p-6 text-center text-xs text-content-muted">
              No active trades
            </div>
          )}
          {trades.map((t) => (
            <div
              key={t.trade_id}
              className="rounded-xl border border-border bg-surface-1 p-3"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-brand text-sm">{t.symbol}</span>
                <DirectionPill dir={t.direction} />
              </div>
              <div className="grid grid-cols-2 gap-2 mt-2 text-[11px]">
                <Field label="Entry" value={formatCurrency(Number(t.entry_price))} />
                <Field label="Current" value={formatCurrency(Number(t.current_price))} />
                <Field label="SL" value={formatCurrency(Number(t.stop_loss))} />
                <Field
                  label="TP1"
                  value={t.tp1_price > 0 ? formatCurrency(Number(t.tp1_price)) : '—'}
                />
                <Field
                  label="Lot"
                  value={`${formatVolume(Number(t.remaining_lot_size))} / ${formatVolume(
                    Number(t.total_lot_size),
                  )}`}
                />
                <Field
                  label="P&L"
                  value={formatCurrency(Number(t.unrealized_pnl))}
                  valueClass={
                    Number(t.unrealized_pnl) >= 0 ? 'text-success' : 'text-danger'
                  }
                />
              </div>
              <div className="mt-2 flex items-center justify-between">
                <ProgressDots be={t.breakeven_set} tp1={t.tp1_hit} tp2={t.tp2_hit} />
                <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-brand-soft text-brand">
                  {t.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Pending Orders */}
      <section aria-labelledby="pending-heading">
        <h2 id="pending-heading" className="text-sm font-semibold text-content mb-3">
          Pending Orders
        </h2>

        {/* Desktop table */}
        <div className="hidden md:block rounded-xl border border-border bg-surface-1 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 z-10 bg-surface-2">
                <tr className="border-b border-border text-content-muted">
                  <Th>Symbol</Th>
                  <Th>Dir</Th>
                  <Th align="right">Price</Th>
                  <Th align="right">SL</Th>
                  <Th align="right">TP</Th>
                  <Th align="right">Volume</Th>
                  <Th align="center">Action</Th>
                </tr>
              </thead>
              <tbody>
                {pending.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-content-muted">
                      No pending orders
                    </td>
                  </tr>
                )}
                {pending.map((o) => (
                  <tr
                    key={o.order_id}
                    className="border-b border-border last:border-b-0 hover:bg-surface-2 transition-colors duration-fast"
                  >
                    <Td className="font-bold text-brand">{o.symbol}</Td>
                    <Td>
                      <DirectionPill dir={o.direction || ''} />
                    </Td>
                    <Td align="right">{formatCurrency(Number(o.price ?? 0))}</Td>
                    <Td align="right" className="text-content-muted">
                      {o.sl ? formatCurrency(Number(o.sl)) : '—'}
                    </Td>
                    <Td align="right" className="text-content-muted">
                      {o.tp ? formatCurrency(Number(o.tp)) : '—'}
                    </Td>
                    <Td align="right">{o.volume ? formatVolume(Number(o.volume)) : '—'}</Td>
                    <Td align="center">
                      <button
                        onClick={() =>
                          cancelOrder.mutate({ order_id: String(o.order_id) })
                        }
                        disabled={cancelOrder.isPending}
                        className="inline-flex items-center gap-1 rounded bg-danger-soft text-danger px-2 py-1 text-[10px] font-medium
                                   hover:bg-danger/20 transition-colors duration-fast disabled:opacity-50 focus-ring"
                      >
                        <X size={10} /> Cancel
                      </button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Mobile cards */}
        <div className="md:hidden space-y-2">
          {pending.length === 0 && (
            <div className="rounded-xl border border-border bg-surface-1 p-6 text-center text-xs text-content-muted">
              No pending orders
            </div>
          )}
          {pending.map((o) => (
            <div
              key={o.order_id}
              className="rounded-xl border border-border bg-surface-1 p-3"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-brand text-sm">{o.symbol}</span>
                <DirectionPill dir={o.direction || ''} />
              </div>
              <div className="grid grid-cols-2 gap-2 mt-2 text-[11px]">
                <Field label="Price" value={formatCurrency(Number(o.price ?? 0))} />
                <Field label="Volume" value={o.volume ? formatVolume(Number(o.volume)) : '—'} />
                <Field label="SL" value={o.sl ? formatCurrency(Number(o.sl)) : '—'} />
                <Field label="TP" value={o.tp ? formatCurrency(Number(o.tp)) : '—'} />
              </div>
              <div className="mt-3 flex justify-end">
                <button
                  onClick={() => cancelOrder.mutate({ order_id: String(o.order_id) })}
                  disabled={cancelOrder.isPending}
                  className="inline-flex items-center gap-1 rounded bg-danger-soft text-danger px-3 py-1.5 text-[11px] font-medium
                             hover:bg-danger/20 transition-colors duration-fast disabled:opacity-50 focus-ring"
                >
                  <X size={12} /> Cancel
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  valueClass = 'text-content',
  accessory,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  valueClass?: string;
  accessory?: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface-1 p-3 sm:p-4 flex items-start gap-3 shadow-card">
      <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-brand-soft text-brand flex-shrink-0">
        {icon}
      </div>
      <div className="flex flex-col gap-0.5 min-w-0">
        <span className="text-[10px] font-medium text-content-muted uppercase tracking-wide">
          {label}
        </span>
        <div className="flex items-center gap-2">
          <span className={`text-base sm:text-lg font-bold ${valueClass}`}>{value}</span>
          {accessory}
        </div>
      </div>
    </div>
  );
}

function DirectionPill({ dir }: { dir: string }) {
  const norm = String(dir || '').toUpperCase();
  const isBuy = norm === 'BUY' || norm === 'LONG';
  const isSell = norm === 'SELL' || norm === 'SHORT';
  const cls = isBuy
    ? 'bg-success-soft text-success'
    : isSell
    ? 'bg-danger-soft text-danger'
    : 'bg-surface-3 text-content-muted';
  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide ${cls}`}>
      {norm || '—'}
    </span>
  );
}

function ProgressDots({ be, tp1, tp2 }: { be: boolean; tp1: boolean; tp2: boolean }) {
  const dot = (active: boolean, label: string) => (
    <span
      className={`flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider
                  ${active ? 'text-success' : 'text-content-faint'}`}
      title={label}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-success' : 'bg-content-faint/40'}`}
      />
      {label}
    </span>
  );
  return (
    <div className="flex items-center justify-center gap-2">
      {dot(be, 'BE')}
      {dot(tp1, 'TP1')}
      {dot(tp2, 'TP2')}
    </div>
  );
}

function Th({
  children,
  align = 'left',
}: {
  children: React.ReactNode;
  align?: 'left' | 'right' | 'center';
}) {
  return (
    <th
      className={`px-4 py-2.5 font-medium text-[10px] uppercase tracking-wider whitespace-nowrap
                   text-${align}`}
    >
      {children}
    </th>
  );
}

function Td({
  children,
  align = 'left',
  className,
}: {
  children: React.ReactNode;
  align?: 'left' | 'right' | 'center';
  className?: string;
}) {
  return (
    <td
      className={`px-4 py-2.5 text-${align} whitespace-nowrap ${className ?? ''}`}
    >
      {children}
    </td>
  );
}

function Field({
  label,
  value,
  valueClass = 'text-content',
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex flex-col">
      <span className="text-[9px] font-semibold uppercase tracking-wider text-content-muted">
        {label}
      </span>
      <span className={`font-medium ${valueClass}`}>{value}</span>
    </div>
  );
}
