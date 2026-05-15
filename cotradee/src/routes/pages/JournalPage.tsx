import { useState, useRef } from 'react';
import { useTradeJournal, usePerformanceMetrics } from '@/features/journal/api/journal';
import { formatCurrency, formatPercentage, formatDateTime, formatAssetPrice } from '@/utils/formatters';
import { CalendarDays } from 'lucide-react';
import PnLCalendar from '@/features/journal/components/PnLCalendar';

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
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ startX: number; startY: number; initX: number; initY: number; hasMoved: boolean } | null>(null);

  const onPointerDown = (e: React.PointerEvent<HTMLButtonElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initX: pos.x,
      initY: pos.y,
      hasMoved: false,
    };
  };

  const onPointerMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    if (!dragRef.current.hasMoved && (Math.abs(dx) > 3 || Math.abs(dy) > 3)) {
      dragRef.current.hasMoved = true;
    }
    if (dragRef.current.hasMoved) {
      setPos({ x: dragRef.current.initX + dx, y: dragRef.current.initY + dy });
    }
  };

  const onPointerUp = (e: React.PointerEvent<HTMLButtonElement>) => {
    e.currentTarget.releasePointerCapture(e.pointerId);
    if (dragRef.current && !dragRef.current.hasMoved) {
      setCalendarOpen(true);
    }
    dragRef.current = null;
  };

  const { data: journal, isLoading } = useTradeJournal({ limit: 50 });
  const { data: metrics } = usePerformanceMetrics(period);

  const entries = (journal?.entries ?? []) as JournalEntry[];
  const total = (journal?.total_count ?? entries.length) as number;

  return (
    <div className="p-4 sm:p-6 space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-black tracking-tight text-content">Trade Journal</h1>
          <span className="text-xs font-bold text-content-muted">({total})</span>
        </div>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value as Period)}
          className="rounded-2xl border border-border bg-white dark:bg-black px-4 py-2 text-xs font-bold text-content
                     shadow-sm focus-ring focus:border-brand transition-all duration-fast w-full sm:w-auto"
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
            metrics?.avg_r_multiple != null
              ? Number(metrics.avg_r_multiple).toFixed(2)
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

      {calendarOpen && <PnLCalendar onClose={() => setCalendarOpen(false)} />}

      {/* Desktop table */}
      <div className="hidden md:block rounded-2xl border border-border bg-white dark:bg-black overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 z-10 bg-surface-1">
              <tr className="border-b border-border text-content-muted">
                <Th className="w-[12%]">Symbol</Th>
                <Th className="w-[8%]">Dir</Th>
                <Th className="w-[14%]">Style</Th>
                <Th align="right" className="w-[12%]">Entry</Th>
                <Th align="right" className="w-[12%]">Exit</Th>
                <Th align="right" className="w-[12%]">P&amp;L</Th>
                <Th align="right" className="w-[8%]">R</Th>
                <Th align="center" className="w-[8%]">Outcome</Th>
                <Th align="right" className="w-[14%]">Closed</Th>
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
                  <Td className="font-bold text-content">{e.symbol}</Td>
                  <Td>{e.direction}</Td>
                  <Td className="text-content-muted">{e.trading_style}</Td>
                  <Td align="right">{formatAssetPrice(e.symbol, Number(e.entry_price))}</Td>
                  <Td align="right">{formatAssetPrice(e.symbol, Number(e.exit_price))}</Td>
                  <Td
                    align="right"
                    className={`font-medium ${
                      Number(e.gross_pnl) >= 0 ? 'text-success' : 'text-danger'
                    }`}
                  >
                    {formatCurrency(Number(e.gross_pnl))}
                  </Td>
                  <Td align="right">{Number(e.r_multiple).toFixed(2)}</Td>
                  <Td align="center">
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
      <div className="md:hidden space-y-3">
        {isLoading && (
          <>
            <div className="rounded-2xl border border-border bg-white dark:bg-black p-5 shadow-sm">
              <div className="h-3 skeleton w-1/3 mb-2" />
              <div className="h-3 skeleton w-2/3" />
            </div>
          </>
        )}
        {!isLoading && entries.length === 0 && (
          <div className="rounded-2xl border border-border bg-white dark:bg-black p-8 text-center text-[13px] font-bold text-content-muted">
            No closed trades yet.
          </div>
        )}
        {entries.map((e) => (
          <div
            key={e.trade_id}
            className="rounded-2xl border border-border bg-white dark:bg-black p-4 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-content text-sm">{e.symbol}</span>
              <OutcomeChip outcome={e.outcome} />
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2 text-[11px]">
              <Field label="Direction" value={e.direction} />
              <Field label="Style" value={e.trading_style} />
              <Field label="Entry" value={formatAssetPrice(e.symbol, Number(e.entry_price))} />
              <Field label="Exit" value={formatAssetPrice(e.symbol, Number(e.exit_price))} />
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

      {/* Floating Action Button for PnL Calendar */}
      <div
        className="fixed bottom-6 right-6 sm:bottom-8 sm:right-8 z-40 touch-none"
        style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}
      >
        <button
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          className="flex items-center justify-center w-14 h-14 rounded-2xl border border-border bg-white dark:bg-black text-content shadow-pop hover:scale-105 transition-all duration-300 group cursor-grab active:cursor-grabbing"
          aria-label="Open PnL Calendar"
          id="pnl-calendar-fab"
        >
          <CalendarDays size={24} className="group-hover:animate-pulse pointer-events-none text-brand" />
        </button>
      </div>
    </div>
  );
}

function OutcomeChip({ outcome }: { outcome: string }) {
  const isWin = String(outcome).toUpperCase() === 'WIN';
  return (
    <span
      className={`px-2.5 py-1 rounded-lg text-[10px] font-bold ${
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
    <div className="rounded-2xl border border-border bg-white dark:bg-black p-4 shadow-sm transition-all hover:border-brand/30">
      <span className="text-[11px] font-bold text-content-muted block mb-1.5">
        {label}
      </span>
      <span className={`text-base sm:text-lg font-black ${valueClass}`}>{value}</span>
    </div>
  );
}

function Th({
  children,
  align = 'left',
  className,
}: {
  children: React.ReactNode;
  align?: 'left' | 'right' | 'center';
  className?: string;
}) {
  return (
    <th
      className={`px-4 py-3 font-bold text-[11px] text-content-muted tracking-tight whitespace-nowrap text-${align} ${className ?? ''}`}
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
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] font-bold text-content-muted">
        {label}
      </span>
      <span className={`font-black text-xs ${valueClass}`}>{value}</span>
    </div>
  );
}
