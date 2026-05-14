import { useCallback } from 'react';
import type { JournalRow } from '../../types';

interface Props {
  value: JournalRow[];
  editing: boolean;
  onChange: (next: JournalRow[]) => void;
}

// 25-column layout, lockstep with PRACTICE.md's final spec. Widths
// are tuned per column so the table stays readable on a wide screen
// and scrolls horizontally on narrow ones (the table container
// already wraps the body in overflow-x-auto). Categorical columns
// (Session, Setup Type, HTF Bias, Outcome, Rule Followed?, etc.)
// get a moderate width to fit single-word values; numeric cells
// stay tight; Notes and Screenshot Link get extra room.
const COLUMNS: Array<{ key: keyof JournalRow; label: string; width: string }> = [
  { key: 'date',                 label: 'Date',                 width: 'w-24'              },
  { key: 'session',              label: 'Session',              width: 'w-24'              },
  { key: 'pair',                 label: 'Pair',                 width: 'w-20'              },
  { key: 'direction',            label: 'Direction',            width: 'w-24'              },
  { key: 'style',                label: 'Style',                width: 'w-24'              },
  { key: 'setup_type',           label: 'Setup Type',           width: 'w-28'              },
  { key: 'htf_bias',             label: 'HTF Bias',             width: 'w-24'              },
  { key: 'entry',                label: 'Entry',                width: 'w-24'              },
  { key: 'stop_loss',            label: 'Stop Loss',            width: 'w-24'              },
  { key: 'take_profit',          label: 'Take Profit',          width: 'w-24'              },
  { key: 'risk_percent',         label: 'Risk %',               width: 'w-20'              },
  { key: 'position_size',        label: 'Position Size',        width: 'w-28'              },
  { key: 'exit',                 label: 'Exit',                 width: 'w-24'              },
  { key: 'rr_planned',           label: 'RR Planned',           width: 'w-24'              },
  { key: 'rr_achieved',          label: 'RR Achieved',          width: 'w-24'              },
  { key: 'pnl',                  label: 'P&L',                  width: 'w-20'              },
  { key: 'outcome',              label: 'Outcome',              width: 'w-20'              },
  { key: 'rule_followed',        label: 'Rule Followed?',       width: 'w-28'              },
  { key: 'emotion_before_trade', label: 'Emotion Before Trade', width: 'w-32'              },
  { key: 'emotion_after_trade',  label: 'Emotion After Trade',  width: 'w-32'              },
  { key: 'trade_quality',        label: 'Trade Quality',        width: 'w-24'              },
  { key: 'mistake_category',     label: 'Mistake Category',     width: 'w-36'              },
  { key: 'news_present',         label: 'News Present?',        width: 'w-28'              },
  { key: 'screenshot_link',      label: 'Screenshot Link',      width: 'min-w-[12rem]'     },
  { key: 'notes',                label: 'Notes',                width: 'min-w-[14rem]'     },
];

function emptyRow(): JournalRow {
  return {
    date: '', session: '', pair: '', direction: '', style: '',
    setup_type: '', htf_bias: '', entry: '', stop_loss: '',
    take_profit: '', risk_percent: '', position_size: '', exit: '',
    rr_planned: '', rr_achieved: '', pnl: '', outcome: '',
    rule_followed: '', emotion_before_trade: '', emotion_after_trade: '',
    trade_quality: '', mistake_category: '', news_present: '',
    screenshot_link: '', notes: '',
  };
}

/**
 * Section 3 — Daily Execution Journal.
 *
 * The core operational table. 10 columns mirror PRACTICE.md:
 *
 *   Date | Pair | Direction | Style | Entry | Exit | RR | P&L | Outcome | Notes
 *
 * The LLM seeds blank rows on generation; the trader fills them in
 * manually as they trade through the 90-day window. Add/remove
 * affordances are surfaced only in edit mode.
 */
export function JournalSection({ value, editing, onChange }: Props) {
  const setCell = useCallback(
    (idx: number, key: keyof JournalRow, v: string) => {
      const next = value.slice();
      next[idx] = { ...next[idx], [key]: v };
      onChange(next);
    },
    [value, onChange],
  );

  const addRow = useCallback(() => {
    onChange([...value, emptyRow()]);
  }, [value, onChange]);

  const removeRow = useCallback(
    (idx: number) => {
      const next = value.slice();
      next.splice(idx, 1);
      onChange(next);
    },
    [value, onChange],
  );

  return (
    <section className="rounded-lg border border-border bg-surface p-4 sm:p-5">
      <header className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-content">Daily Execution Journal</h3>
          <p className="mt-0.5 text-xs text-content-muted">
            Record every trade. Add rows as you trade through the quarter.
          </p>
        </div>
        {editing && (
          <button
            type="button"
            onClick={addRow}
            className="shrink-0 rounded bg-brand px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand/90 focus-ring"
          >
            + Add row
          </button>
        )}
      </header>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wide text-content-muted">
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  className={`${c.width} border-b border-border px-2 py-1.5 font-medium`}
                >
                  {c.label}
                </th>
              ))}
              {editing && <th className="w-10 border-b border-border" aria-label="actions" />}
            </tr>
          </thead>
          <tbody>
            {value.length === 0 && (
              <tr>
                <td
                  colSpan={editing ? COLUMNS.length + 1 : COLUMNS.length}
                  className="py-8 text-center text-content-muted"
                >
                  No journal rows yet. {editing ? 'Click + Add row to start.' : ''}
                </td>
              </tr>
            )}
            {value.map((row, idx) => (
              <tr key={idx} className="border-b border-border/60">
                {COLUMNS.map((c) => (
                  <td key={c.key} className="px-1 py-0.5">
                    {editing ? (
                      <input
                        type="text"
                        value={row[c.key]}
                        onChange={(e) => setCell(idx, c.key, e.target.value)}
                        className="w-full rounded border border-transparent bg-app px-1.5 py-1 text-content placeholder:text-content-muted focus:border-border focus-ring"
                        aria-label={`${c.label} row ${idx + 1}`}
                      />
                    ) : (
                      <span className="block px-1.5 py-1 text-content">
                        {row[c.key] || ''}
                      </span>
                    )}
                  </td>
                ))}
                {editing && (
                  <td className="px-1 text-center">
                    <button
                      type="button"
                      onClick={() => removeRow(idx)}
                      className="rounded p-1 text-content-muted hover:text-danger focus-ring"
                      aria-label={`Remove row ${idx + 1}`}
                      title="Remove row"
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
