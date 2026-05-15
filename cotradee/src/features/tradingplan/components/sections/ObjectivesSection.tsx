import { useCallback } from 'react';
import type { Objectives } from '../../types';

interface Props {
  value: Objectives;
  editing: boolean;
  onChange: (next: Objectives) => void;
}

/**
 * Section 6 — 90-Day Objectives.
 *
 * Behavioural-only objectives ("Maintain consistency for 30 days",
 * "Reduce impulsive entries"). PRACTICE.md is explicit: NO profit
 * promises. The backend validator enforces this for both LLM-
 * generated and user-edited objectives, so a slip here is caught
 * before persistence.
 */
export function ObjectivesSection({ value, editing, onChange }: Props) {
  const setItem = useCallback(
    (idx: number, v: string) => {
      const next = value.items.slice();
      next[idx] = v;
      onChange({ items: next });
    },
    [value, onChange],
  );

  const addItem = useCallback(() => {
    onChange({ items: [...value.items, ''] });
  }, [value, onChange]);

  const removeItem = useCallback(
    (idx: number) => {
      const next = value.items.slice();
      next.splice(idx, 1);
      onChange({ items: next });
    },
    [value, onChange],
  );

  return (
    <section className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm">
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 mb-1">Section 06</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">90-Day Objectives</h3>
          <p className="mt-1 text-xs font-medium text-black/40 dark:text-white/40 leading-relaxed max-w-xl">
            Behavioural goals only. Profit targets and compounding fantasies are off-limits.
          </p>
        </div>
        {editing && (
          <button
            type="button"
            onClick={addItem}
            className="shrink-0 rounded-xl bg-black dark:bg-white px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all"
          >
            + Add objective
          </button>
        )}
      </header>
      <ol className="space-y-4">
        {value.items.map((o, idx) => (
          <li key={idx} className="flex items-start gap-4">
            <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 text-[10px] font-black text-black dark:text-white">
              {String(idx + 1).padStart(2, '0')}
            </span>
            {editing ? (
              <input
                type="text"
                value={o}
                onChange={(e) => setItem(idx, e.target.value)}
                className="flex-1 rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-2 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
                aria-label={`Objective ${idx + 1}`}
              />
            ) : (
              <span className="flex-1 text-sm font-medium text-black/60 dark:text-white/60 leading-relaxed">{o}</span>
            )}
            {editing && (
              <button
                type="button"
                onClick={() => removeItem(idx)}
                className="shrink-0 rounded-lg p-2 text-black/20 dark:text-white/20 hover:text-red-500 hover:bg-red-500/10 transition-all font-black text-sm"
                aria-label={`Remove objective ${idx + 1}`}
                title="Remove"
              >
                ×
              </button>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
