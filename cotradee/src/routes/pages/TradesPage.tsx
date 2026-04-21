import { useManagedTrades } from '@/features/journal/api/journal';
import { useExecutionState, useCancelOrder } from '@/features/execution/api/brokerAccount';
import { formatCurrency } from '@/utils/formatters';
import { X } from 'lucide-react';

export default function TradesPage() {
  const { data: managed } = useManagedTrades();
  const { data: execState } = useExecutionState();
  const cancelOrder = useCancelOrder();

  const trades = managed ?? [];
  const pending = execState?.pending_orders ?? [];

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Active Managed Trades */}
      <section>
        <h2 className="text-sm font-semibold text-content mb-3">Active Managed Trades</h2>
        <div className="rounded-xl border border-border bg-surface-1 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border text-content-muted">
                <th className="text-left px-4 py-2.5 font-medium">Symbol</th>
                <th className="text-left px-4 py-2.5 font-medium">Direction</th>
                <th className="text-right px-4 py-2.5 font-medium">Entry</th>
                <th className="text-right px-4 py-2.5 font-medium">Current</th>
                <th className="text-right px-4 py-2.5 font-medium">SL</th>
                <th className="text-right px-4 py-2.5 font-medium">P&L</th>
                <th className="text-center px-4 py-2.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {trades.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-content-muted">No active trades</td></tr>
              )}
              {trades.map((t: Record<string, unknown>) => (
                <tr key={String(t.trade_id)} className="border-b border-border last:border-b-0 hover:bg-surface-2 transition-colors">
                  <td className="px-4 py-2.5 font-bold text-brand">{String(t.symbol)}</td>
                  <td className="px-4 py-2.5">{String(t.direction)}</td>
                  <td className="px-4 py-2.5 text-right">{formatCurrency(Number(t.entry_price))}</td>
                  <td className="px-4 py-2.5 text-right">{formatCurrency(Number(t.current_price))}</td>
                  <td className="px-4 py-2.5 text-right text-content-muted">{formatCurrency(Number(t.stop_loss))}</td>
                  <td className={`px-4 py-2.5 text-right font-medium ${Number(t.unrealized_pnl) >= 0 ? 'text-success' : 'text-danger'}`}>
                    {formatCurrency(Number(t.unrealized_pnl))}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-brand/10 text-brand">
                      {String(t.status)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Pending Orders */}
      <section>
        <h2 className="text-sm font-semibold text-content mb-3">Pending Orders</h2>
        <div className="rounded-xl border border-border bg-surface-1 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border text-content-muted">
                <th className="text-left px-4 py-2.5 font-medium">Symbol</th>
                <th className="text-left px-4 py-2.5 font-medium">Type</th>
                <th className="text-right px-4 py-2.5 font-medium">Price</th>
                <th className="text-right px-4 py-2.5 font-medium">Volume</th>
                <th className="text-center px-4 py-2.5 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {pending.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-content-muted">No pending orders</td></tr>
              )}
              {pending.map((o: Record<string, unknown>) => (
                <tr key={String(o.order_id ?? o.OrderID)} className="border-b border-border last:border-b-0 hover:bg-surface-2 transition-colors">
                  <td className="px-4 py-2.5 font-bold text-brand">{String(o.symbol ?? o.Symbol)}</td>
                  <td className="px-4 py-2.5">{String(o.type ?? o.Type ?? '-')}</td>
                  <td className="px-4 py-2.5 text-right">{formatCurrency(Number(o.price ?? o.Price ?? 0))}</td>
                  <td className="px-4 py-2.5 text-right">{String(o.volume ?? o.Volume ?? '-')}</td>
                  <td className="px-4 py-2.5 text-center">
                    <button
                      onClick={() => cancelOrder.mutate({ order_id: String(o.order_id ?? o.OrderID) })}
                      disabled={cancelOrder.isPending}
                      className="inline-flex items-center gap-1 rounded bg-danger/10 text-danger px-2 py-1 text-[10px] font-medium
                                 hover:bg-danger/20 transition-colors disabled:opacity-50"
                    >
                      <X size={10} /> Cancel
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
