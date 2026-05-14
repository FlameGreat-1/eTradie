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
    <section className="rounded-lg border border-border bg-surface p-4 sm:p-5">
      <header className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-content">90-Day Objectives</h3>
          <p className="mt-0.5 text-xs text-content-muted">
            Behavioural goals only. Profit targets and compounding fantasies are off-limits.
          </p>
        </div>
        {editing && (
          <button
            type="button"
            onClick={addItem}
            className="shrink-0 rounded bg-brand px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand/90 focus-ring"
          >
            + Add objective
          </button>
        )}
      </header>
      <ol className="space-y-2">
        {value.items.map((o, idx) => (
          <li key={idx} className="flex items-start gap-3">
            <span className="mt-1 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand/10 text-[11px] font-semibold text-brand">
              {idx + 1}
            </span>
            {editing ? (
              <input
                type="text"
                value={o}
                onChange={(e) => setItem(idx, e.target.value)}
                className="flex-1 rounded border border-border bg-app px-2 py-1 text-sm text-content focus-ring"
                aria-label={`Objective ${idx + 1}`}
              />
            ) : (
              <span className="flex-1 text-sm text-content-secondary">{o}</span>
            )}
            {editing && (
              <button
                type="button"
                onClick={() => removeItem(idx)}
                className="shrink-0 rounded p-1 text-content-muted hover:text-danger focus-ring"
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
