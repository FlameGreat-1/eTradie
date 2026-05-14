import { useCallback } from 'react';
import type { AccountParameters } from '../../types';

interface Props {
  value: AccountParameters;
  editing: boolean;
  onChange: (next: AccountParameters) => void;
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
export function AccountParametersSection({ value, editing, onChange }: Props) {
  const handle = useCallback(
    (key: keyof AccountParameters) => (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ ...value, [key]: e.target.value });
    },
    [value, onChange],
  );

  return (
    <section className="rounded-lg border border-border bg-surface p-4 sm:p-5">
      <header className="mb-3">
        <h3 className="text-base font-semibold text-content">Account Parameters</h3>
        <p className="mt-0.5 text-xs text-content-muted">
          Your live risk envelope for the next 90 days.
        </p>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-content-muted">
              <th className="w-1/2 py-1.5 pr-3 font-medium">Parameter</th>
              <th className="py-1.5 font-medium">Value</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map(({ key, label }) => (
              <tr key={key} className="border-t border-border">
                <td className="py-2 pr-3 text-content-secondary">{label}</td>
                <td className="py-2">
                  {editing ? (
                    <input
                      type="text"
                      value={value[key]}
                      onChange={handle(key)}
                      className="w-full rounded border border-border bg-app px-2 py-1 text-content focus-ring"
                      aria-label={label}
                    />
                  ) : (
                    <span className="text-content">{value[key] || '—'}</span>
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
