import { useCallback } from 'react';
import type { DisciplineScorecard, DisciplineScorecardItem } from '../../types';

interface Props {
  value: DisciplineScorecard;
  editing: boolean;
  onChange: (next: DisciplineScorecard) => void;
}

/**
 * Section 5 — Discipline Scorecard.
 *
 * Per-metric score (text — "8/10", "A", or whatever the trader
 * prefers). Editable in both metric and score columns when in edit
 * mode so the trader can swap out an LLM-suggested metric they don't
 * care about (e.g. replace "Patience" with "Pre-trade checklist
 * completed").
 */
export function ScorecardSection({ value, editing, onChange }: Props) {
  const setItem = useCallback(
    (idx: number, patch: Partial<DisciplineScorecardItem>) => {
      const next = value.items.slice();
      next[idx] = { ...next[idx], ...patch };
      onChange({ items: next });
    },
    [value, onChange],
  );

  const addItem = useCallback(() => {
    onChange({ items: [...value.items, { metric: '', score: '' }] });
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
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 mb-1">Section 05</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Discipline Scorecard</h3>
          <p className="mt-1 text-xs font-medium text-black/40 dark:text-white/40 leading-relaxed">
            Rate yourself weekly. Be honest — the table only works if you are.
          </p>
        </div>
        {editing && (
          <button
            type="button"
            onClick={addItem}
            className="shrink-0 rounded-xl bg-black dark:bg-white px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all"
          >
            + Add metric
          </button>
        )}
      </header>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[10px] font-black uppercase tracking-widest text-black/20 dark:text-white/20">
              <th className="w-2/3 py-2 pr-3">Metric</th>
              <th className="py-2">Score</th>
              {editing && <th className="w-10" aria-label="actions" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-black/5 dark:divide-white/5">
            {value.items.map((it, idx) => (
              <tr key={idx}>
                <td className="py-3 pr-3">
                  {editing ? (
                    <input
                      type="text"
                      value={it.metric}
                      onChange={(e) => setItem(idx, { metric: e.target.value })}
                      className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black px-3 py-1.5 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
                      aria-label={`Metric ${idx + 1}`}
                    />
                  ) : (
                    <span className="text-sm font-bold text-black/60 dark:text-white/60 tracking-tight">{it.metric}</span>
                  )}
                </td>
                <td className="py-2">
                  {editing ? (
                    <input
                      type="text"
                      value={it.score}
                      placeholder="e.g. 8/10"
                      onChange={(e) => setItem(idx, { score: e.target.value })}
                      className="w-32 rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black px-3 py-1.5 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
                      aria-label={`Score ${idx + 1}`}
                    />
                  ) : (
                    <span className="text-sm font-bold text-black dark:text-white tabular-nums tracking-tighter">{it.score || '—'}</span>
                  )}
                </td>
                {editing && (
                  <td className="text-right py-2">
                    <button
                      type="button"
                      onClick={() => removeItem(idx)}
                      className="rounded-lg p-2 text-black/20 dark:text-white/20 hover:text-red-500 hover:bg-red-500/10 transition-all font-black text-sm"
                      aria-label={`Remove ${it.metric || `metric ${idx + 1}`}`}
                      title="Remove"
                    >
                      ×
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
