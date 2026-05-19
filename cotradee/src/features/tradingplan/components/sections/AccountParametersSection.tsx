import { useCallback } from 'react';
import type { AccountParameters } from '../../types';

interface Props {
  value: AccountParameters;
  editing: boolean;
  onChange: (next: AccountParameters) => void;
  headerActions?: React.ReactNode;
}

const ROWS: Array<{ key: keyof AccountParameters; label: string }> = [
  { key: 'starting_balance', label: 'Starting Balance' },
  { key: 'max_daily_risk', label: 'Max Daily Risk' },
  { key: 'max_weekly_drawdown', label: 'Max Weekly Drawdown' },
  { key: 'preferred_rr', label: 'Preferred RR' },
  { key: 'max_trades_per_day', label: 'Max Trades Per Day' },
  { key: 'trading_days_per_week', label: 'Trading Days Per Week' },
];

/**
 * Section 2 — Account Parameters.
 *
 * 6-row parameter / value table. Editable when `editing` is true so
 * the trader can override the LLM-suggested values without
 * regenerating the whole plan (e.g. drop max-daily-risk from 1% to
 * 0.5% mid-quarter).
 */
export function AccountParametersSection({ value, editing, onChange, headerActions }: Props) {
  const handle = useCallback(
    (key: keyof AccountParameters) => (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ ...value, [key]: e.target.value });
    },
    [value, onChange],
  );

  return (
    <section className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm">
      <header className="mb-4 flex items-start justify-between gap-2 sm:gap-4">
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 mb-1">Section 02</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Account Parameters</h3>
          <p className="mt-1 text-[10px] sm:text-xs font-medium text-black/40 dark:text-white/40 leading-relaxed">
            Your live risk envelope for the next 90 days.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {headerActions}
        </div>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[10px] font-black uppercase tracking-widest text-black/20 dark:text-white/20">
              <th className="w-1/2 py-2 pr-3">Parameter</th>
              <th className="py-2 text-right">Value</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map(({ key, label }) => (
              <tr key={key} className="border-t border-black/5 dark:border-white/5">
                <td className="py-3 pr-3 text-[11px] font-black uppercase tracking-wider text-black/40 dark:text-white/40">{label}</td>
                <td className="py-2 text-right">
                  {editing ? (
                    <input
                      type="text"
                      value={value[key]}
                      onChange={handle(key)}
                      className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black px-3 py-1.5 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none text-right"
                      aria-label={label}
                    />
                  ) : (
                    <span className="text-sm font-bold text-black dark:text-white tracking-tight">{value[key] || '—'}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
