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
    <section className="rounded-lg border border-border bg-surface p-4 sm:p-5">
      <header className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-content">Discipline Scorecard</h3>
          <p className="mt-0.5 text-xs text-content-muted">
            Rate yourself weekly. Be honest — the table only works if you are.
          </p>
        </div>
        {editing && (
          <button
            type="button"
            onClick={addItem}
            className="shrink-0 rounded bg-brand px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand/90 focus-ring"
          >
            + Add metric
          </button>
        )}
      </header>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-content-muted">
              <th className="w-2/3 py-1.5 pr-3 font-medium">Metric</th>
              <th className="py-1.5 font-medium">Score</th>
              {editing && <th className="w-10" aria-label="actions" />}
            </tr>
          </thead>
          <tbody>
            {value.items.map((it, idx) => (
              <tr key={idx} className="border-t border-border">
                <td className="py-1.5 pr-3">
                  {editing ? (
                    <input
                      type="text"
                      value={it.metric}
                      onChange={(e) => setItem(idx, { metric: e.target.value })}
                      className="w-full rounded border border-border bg-app px-2 py-1 text-content focus-ring"
                      aria-label={`Metric ${idx + 1}`}
                    />
                  ) : (
                    <span className="text-content-secondary">{it.metric}</span>
                  )}
                </td>
                <td className="py-1.5">
                  {editing ? (
                    <input
                      type="text"
                      value={it.score}
                      placeholder="e.g. 8/10"
                      onChange={(e) => setItem(idx, { score: e.target.value })}
                      className="w-32 rounded border border-border bg-app px-2 py-1 text-content focus-ring"
                      aria-label={`Score ${idx + 1}`}
                    />
                  ) : (
                    <span className="text-content tabular-nums">{it.score || '—'}</span>
                  )}
                </td>
                {editing && (
                  <td className="text-right">
                    <button
                      type="button"
                      onClick={() => removeItem(idx)}
                      className="rounded p-1 text-content-muted hover:text-danger focus-ring"
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
