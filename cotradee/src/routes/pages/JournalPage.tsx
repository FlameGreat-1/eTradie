import { useState } from 'react';
import { useTradeJournal, usePerformanceMetrics } from '@/features/journal/api/journal';
import { formatCurrency, formatPercentage, formatDateTime } from '@/utils/formatters';

export default function JournalPage() {
  const [period, setPeriod] = useState('ALL_TIME');
  const { data: journal } = useTradeJournal({ limit: 50 });
  const { data: metrics } = usePerformanceMetrics(period);

  const entries = journal?.entries ?? [];

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Performance Summary */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-content">Trade Journal</h1>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-xs text-content focus:outline-none focus:border-brand"
        >
          <option value="DAILY">Daily</option>
          <option value="WEEKLY">Weekly</option>
          <option value="MONTHLY">Monthly</option>
          <option value="ALL_TIME">All Time</option>
        </select>
      </div>

      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatBox label="Total Trades" value={String(metrics.total_trades ?? 0)} />
          <StatBox label="Win Rate" value={metrics.win_rate != null ? formatPercentage(metrics.win_rate) : '---'} />
          <StatBox label="Avg R:R" value={metrics.avg_risk_reward != null ? metrics.avg_risk_reward.toFixed(2) : '---'} />
          <StatBox label="Total P&L" value={metrics.total_pnl != null ? formatCurrency(metrics.total_pnl) : '---'}
            valueClass={metrics.total_pnl >= 0 ? 'text-success' : 'text-danger'} />
        </div>
      )}

      {/* Journal Table */}
      <div className="rounded-xl border border-border bg-surface-1 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-content-muted">
              <th className="text-left px-4 py-2.5 font-medium">Symbol</th>
              <th className="text-left px-4 py-2.5 font-medium">Direction</th>
              <th className="text-left px-4 py-2.5 font-medium">Style</th>
              <th className="text-right px-4 py-2.5 font-medium">Entry</th>
              <th className="text-right px-4 py-2.5 font-medium">Exit</th>
              <th className="text-right px-4 py-2.5 font-medium">P&L</th>
              <th className="text-right px-4 py-2.5 font-medium">R Multiple</th>
              <th className="text-left px-4 py-2.5 font-medium">Outcome</th>
              <th className="text-right px-4 py-2.5 font-medium">Closed</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 && (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-content-muted">No closed trades yet</td></tr>
            )}
            {entries.map((e: Record<string, unknown>) => (
              <tr key={String(e.trade_id)} className="border-b border-border last:border-b-0 hover:bg-surface-2 transition-colors">
                <td className="px-4 py-2.5 font-bold text-brand">{String(e.symbol)}</td>
                <td className="px-4 py-2.5">{String(e.direction)}</td>
                <td className="px-4 py-2.5 text-content-muted">{String(e.trading_style)}</td>
                <td className="px-4 py-2.5 text-right">{formatCurrency(Number(e.entry_price))}</td>
                <td className="px-4 py-2.5 text-right">{formatCurrency(Number(e.exit_price))}</td>
                <td className={`px-4 py-2.5 text-right font-medium ${Number(e.gross_pnl) >= 0 ? 'text-success' : 'text-danger'}`}>
                  {formatCurrency(Number(e.gross_pnl))}
                </td>
                <td className="px-4 py-2.5 text-right">{Number(e.r_multiple).toFixed(2)}</td>
                <td className="px-4 py-2.5">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                    e.outcome === 'WIN' ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'
                  }`}>
                    {String(e.outcome)}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right text-content-muted">
                  {e.closed_at ? formatDateTime(String(e.closed_at)) : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatBox({ label, value, valueClass = 'text-content' }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface-1 p-4">
      <span className="text-[10px] font-medium text-content-muted uppercase tracking-wide block mb-1">{label}</span>
      <span className={`text-xl font-bold ${valueClass}`}>{value}</span>
    </div>
  );
}
