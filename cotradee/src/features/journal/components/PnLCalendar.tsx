import { useState, useCallback, useMemo } from 'react';
import { usePnLCalendar } from '@/features/journal/api/journal';
import { useBrokerAccount } from '@/features/execution/api/brokerAccount';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'] as const;

/**
 * Format a PnL value for display.
 * Positive → "+123" or "+1.2K", Negative → "-45.3"
 */
function formatPnL(value: number, currencySymbol: string): string {
  const abs = Math.abs(value);
  const prefix = value >= 0 ? '+' : '-';
  if (abs >= 1000) {
    const k = abs / 1000;
    return `${prefix}${currencySymbol}${k % 1 === 0 ? k.toFixed(0) : k.toFixed(1)}K`;
  }
  if (abs >= 100) return `${prefix}${currencySymbol}${abs.toFixed(0)}`;
  if (abs >= 10) return `${prefix}${currencySymbol}${abs.toFixed(1)}`;
  return `${prefix}${currencySymbol}${abs.toFixed(1)}`;
}

// Minimal symbol map since formatters.ts doesn't export it
const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  JPY: '¥',
};

interface PnLCalendarProps {
  onClose: () => void;
}

export default function PnLCalendar({ onClose }: PnLCalendarProps) {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1); // 1-indexed

  const { data: accountData } = useBrokerAccount();
  const account = accountData?.account as { currency?: string } | undefined;
  const currencyCode = account?.currency || 'USD';
  const currencySymbol = CURRENCY_SYMBOLS[currencyCode] || '$';

  const { data, isLoading } = usePnLCalendar(year, month);

  const goToPrevMonth = useCallback(() => {
    if (month === 1) {
      setMonth(12);
      setYear((y) => y - 1);
    } else {
      setMonth((m) => m - 1);
    }
  }, [month]);

  const goToNextMonth = useCallback(() => {
    if (month === 12) {
      setMonth(1);
      setYear((y) => y + 1);
    } else {
      setMonth((m) => m + 1);
    }
  }, [month]);

  // Calendar grid computation
  const { cells, daysInMonth, startDow } = useMemo(() => {
    const firstDay = new Date(year, month - 1, 1);
    const dow = firstDay.getDay(); // 0=Sun
    const dim = new Date(year, month, 0).getDate();
    const totalCells = dow + dim;
    return { cells: totalCells, daysInMonth: dim, startDow: dow };
  }, [year, month]);

  const dailyPnl = data?.daily_pnl ?? {};
  const currentStreak = data?.current_streak ?? 0;
  const maxStreak = data?.max_streak ?? 0;

  const today = now.getDate();
  const isCurrentMonth = year === now.getFullYear() && month === now.getMonth() + 1;

  const monthLabel = `${year}-${String(month).padStart(2, '0')}`;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 animate-fade-in" onClick={onClose}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" />

      {/* Calendar Card */}
      <div
        className="relative w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden bg-surface-1"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ────────────────────────────────────────── */}
        <div className="flex items-center justify-between gap-1 sm:gap-3 px-3 sm:px-5 pt-5 pb-3">
          <div className="flex items-center gap-1 sm:gap-2.5">
            <h2 className="text-[14px] sm:text-lg font-bold text-content tracking-tight whitespace-nowrap">PnL Calendar</h2>
            <span
              className="flex items-center gap-1 px-1.5 sm:px-2 py-0.5 rounded-full text-[9px] sm:text-[11px] font-semibold bg-surface-2 text-content-muted border border-border"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
              {currencyCode}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 rounded-lg px-2 py-1 bg-surface-2 border border-border">
              <button
                onClick={goToPrevMonth}
                className="p-0.5 rounded hover:bg-surface-3 transition-colors text-content-muted hover:text-content"
                aria-label="Previous month"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-xs sm:text-sm font-semibold text-content min-w-[64px] sm:min-w-[80px] text-center">{monthLabel}</span>
              <button
                onClick={goToNextMonth}
                className="p-0.5 rounded hover:bg-surface-3 transition-colors text-content-muted hover:text-content"
                aria-label="Next month"
              >
                <ChevronRight size={16} />
              </button>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-surface-2 transition-colors text-content-muted hover:text-danger"
              aria-label="Close calendar"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* ── Day-of-week headers ───────────────────────────── */}
        <div className="grid grid-cols-7 px-5 pb-1">
          {DAY_NAMES.map((d) => (
            <div key={d} className="text-center text-[11px] font-semibold py-1.5 text-content-muted uppercase tracking-wider">
              {d}
            </div>
          ))}
        </div>

        {/* ── Calendar Grid ─────────────────────────────────── */}
        <div className="grid grid-cols-7 gap-1 px-5 pb-4">
          {isLoading ? (
            // Skeleton
            Array.from({ length: 35 }).map((_, i) => (
              <div key={i} className="h-14 rounded-lg animate-pulse bg-surface-2" />
            ))
          ) : (
            Array.from({ length: Math.ceil(cells / 7) * 7 }).map((_, i) => {
              const dayNum = i - startDow + 1;
              const isValidDay = dayNum >= 1 && dayNum <= daysInMonth;

              if (!isValidDay) {
                return <div key={i} className="h-14" />;
              }

              const dateKey = `${year}-${String(month).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
              const pnl = dailyPnl[dateKey];
              const hasPnl = pnl !== undefined && pnl !== null;
              const isToday = isCurrentMonth && dayNum === today;

              return (
                <div
                  key={i}
                  className={`relative flex flex-col items-center justify-center h-14 rounded-lg transition-colors border
                    ${hasPnl ? 'bg-surface-2 border-border/50' : 'bg-transparent border-transparent'}`}
                >
                  <span
                    className={`text-sm font-semibold ${hasPnl ? 'text-content' : 'text-content-muted'}`}
                  >
                    {dayNum}
                  </span>
                  {hasPnl && (
                    <span
                      className={`text-[11px] font-bold leading-none mt-0.5 ${pnl >= 0 ? 'text-success' : 'text-danger'}`}
                    >
                      {formatPnL(pnl, currencySymbol)}
                    </span>
                  )}
                  {isToday && (
                    <span
                      className="absolute bottom-0.5 text-[8px] text-brand"
                    >
                      ▲
                    </span>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* ── Footer: Streaks ───────────────────────────────── */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-surface-2 border-t border-border">
          <div className="flex items-center gap-2">
            <span className="text-[12px] font-medium text-content-muted">
              Current Streak:
            </span>
            <span className="text-[13px] font-bold text-content">{currentStreak} d</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-success-soft">
            <span className="text-[12px] font-medium text-success/80">
              Max Streak:
            </span>
            <span className="text-[13px] font-bold text-success">{maxStreak} d</span>
          </div>
        </div>
      </div>
    </div>
  );
}

