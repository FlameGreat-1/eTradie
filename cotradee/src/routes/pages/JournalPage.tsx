import { useState } from 'react';
import { useTradeJournal, usePerformanceMetrics } from '@/features/journal/api/journal';
import { formatCurrency, formatPercentage, formatDateTime } from '@/utils/formatters';
import { BookOpen } from 'lucide-react';

type Period = 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'ALL_TIME';

interface JournalEntry {
  trade_id: string;
  symbol: string;
  direction: string;
  trading_style: string;
  entry_price: number;
  exit_price: number;
  gross_pnl: number;
  r_multiple: number;
  outcome: 'WIN' | 'LOSS' | string;
  closed_at?: string;
}

export default function JournalPage() {
  const [period, setPeriod] = useState<Period>('ALL_TIME');
  const { data: journal, isLoading } = useTradeJournal({ limit: 50 });
  const { data: metrics } = usePerformanceMetrics(period);

  const entries = (journal?.entries ?? []) as JournalEntry[];
  const total = (journal?.total_count ?? entries.length) as number;

  return (
    <div className="p-4 sm:p-6 space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-2">
          <BookOpen size={18} className="text-brand" />
          <h1 className="text-lg font-bold text-content">Trade Journal</h1>
          <span className="text-xs text-content-muted">({total})</span>
        </div>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value as Period)}
          className="rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs text-content
                     focus-ring focus:border-brand transition-colors duration-fast w-full sm:w-auto"
          aria-label="Performance period"
        >
          <option value="DAILY">Daily</option>
          <option value="WEEKLY">Weekly</option>
          <option value="MONTHLY">Monthly</option>
          <option value="ALL_TIME">All Time</option>
        </select>
      </div>

      {/* Performance summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <StatBox label="Total Trades" value={String(metrics?.total_trades ?? 0)} />
        <StatBox
          label="Win Rate"
          value={metrics?.win_rate != null ? formatPercentage(metrics.win_rate) : '---'}
        />
        <StatBox
          label="Avg R:R"
          value={
            metrics?.avg_risk_reward != null
              ? Number(metrics.avg_risk_reward).toFixed(2)
              : '---'
          }
        />
        <StatBox
          label="Total P&L"
          value={metrics?.total_pnl != null ? formatCurrency(metrics.total_pnl) : '---'}
          valueClass={
            metrics?.total_pnl == null
              ? 'text-content'
              : metrics.total_pnl >= 0
              ? 'text-success'
              : 'text-danger'
          }
        />
      </div>

      {/* Desktop table */}
      <div className="hidden md:block rounded-xl border border-border bg-surface-1 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 z-10 bg-surface-2">
              <tr className="border-b border-border text-content-muted">
                <Th>Symbol</Th>
                <Th>Dir</Th>
                <Th>Style</Th>
                <Th align="right">Entry</Th>
                <Th align="right">Exit</Th>
                <Th align="right">P&amp;L</Th>
                <Th align="right">R</Th>
                <Th align="left">Outcome</Th>
                <Th align="right">Closed</Th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={9}>
                    <div className="px-4 py-6 space-y-2">
                      <div className="h-3 skeleton w-full" />
                      <div className="h-3 skeleton w-5/6" />
                      <div className="h-3 skeleton w-4/6" />
                    </div>
                  </td>
                </tr>
              )}
              {!isLoading && entries.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-content-muted">
                    No closed trades yet. They appear here automatically the moment
                    a position closes at the broker.
                  </td>
                </tr>
              )}
              {entries.map((e, i) => (
                <tr
                  key={e.trade_id}
                  className={`border-b border-border last:border-b-0 hover:bg-surface-2 transition-colors duration-fast
                              ${i % 2 === 1 ? 'bg-surface-2/40' : ''}`}
                >
                  <Td className="font-bold text-brand">{e.symbol}</Td>
                  <Td>{e.direction}</Td>
                  <Td className="text-content-muted">{e.trading_style}</Td>
                  <Td align="right">{formatCurrency(Number(e.entry_price))}</Td>
                  <Td align="right">{formatCurrency(Number(e.exit_price))}</Td>
                  <Td
                    align="right"
                    className={`font-medium ${
                      Number(e.gross_pnl) >= 0 ? 'text-success' : 'text-danger'
                    }`}
                  >
                    {formatCurrency(Number(e.gross_pnl))}
                  </Td>
                  <Td align="right">{Number(e.r_multiple).toFixed(2)}</Td>
                  <Td>
                    <OutcomeChip outcome={e.outcome} />
                  </Td>
                  <Td align="right" className="text-content-muted">
                    {e.closed_at ? formatDateTime(String(e.closed_at)) : '—'}
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile card list */}
      <div className="md:hidden space-y-2">
        {isLoading && (
          <>
            <div className="rounded-xl border border-border bg-surface-1 p-4">
              <div className="h-3 skeleton w-1/3 mb-2" />
              <div className="h-3 skeleton w-2/3" />
            </div>
            <div className="rounded-xl border border-border bg-surface-1 p-4">
              <div className="h-3 skeleton w-1/3 mb-2" />
              <div className="h-3 skeleton w-2/3" />
            </div>
          </>
        )}
        {!isLoading && entries.length === 0 && (
          <div className="rounded-xl border border-border bg-surface-1 p-6 text-center text-xs text-content-muted">
            No closed trades yet.
          </div>
        )}
        {entries.map((e) => (
          <div
            key={e.trade_id}
            className="rounded-xl border border-border bg-surface-1 p-3"
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-brand text-sm">{e.symbol}</span>
              <OutcomeChip outcome={e.outcome} />
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2 text-[11px]">
              <Field label="Direction" value={e.direction} />
              <Field label="Style" value={e.trading_style} />
              <Field label="Entry" value={formatCurrency(Number(e.entry_price))} />
              <Field label="Exit" value={formatCurrency(Number(e.exit_price))} />
              <Field
                label="P&L"
                value={formatCurrency(Number(e.gross_pnl))}
                valueClass={Number(e.gross_pnl) >= 0 ? 'text-success' : 'text-danger'}
              />
              <Field label="R" value={Number(e.r_multiple).toFixed(2)} />
            </div>
            <div className="mt-2 text-[10px] text-content-muted">
              {e.closed_at ? formatDateTime(String(e.closed_at)) : '—'}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function OutcomeChip({ outcome }: { outcome: string }) {
  const isWin = String(outcome).toUpperCase() === 'WIN';
  return (
    <span
      className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
        isWin ? 'bg-success-soft text-success' : 'bg-danger-soft text-danger'
      }`}
    >
      {outcome}
    </span>
  );
}

function StatBox({
  label,
  value,
  valueClass = 'text-content',
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface-1 p-3 sm:p-4 shadow-card">
      <span className="text-[10px] font-medium text-content-muted uppercase tracking-wide block mb-1">
        {label}
      </span>
      <span className={`text-base sm:text-xl font-bold ${valueClass}`}>{value}</span>
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
    <td className={`px-4 py-2.5 text-${align} whitespace-nowrap ${className ?? ''}`}>
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
