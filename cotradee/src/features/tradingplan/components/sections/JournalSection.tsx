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
 * The core operational table. 25 columns mirror PRACTICE.md's final
 * spec (Date, Session, Pair, Direction, Style, Setup Type, HTF Bias,
 * Entry, Stop Loss, Take Profit, Risk %, Position Size, Exit,
 * RR Planned, RR Achieved, P&L, Outcome, Rule Followed?,
 * Emotion Before Trade, Emotion After Trade, Trade Quality,
 * Mistake Category, News Present?, Screenshot Link, Notes).
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
    <section className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm overflow-hidden transition-all duration-300">
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 mb-1">Section 03</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Daily Execution Journal</h3>
          <p className="mt-1 text-xs font-medium text-black/40 dark:text-white/40 leading-relaxed max-w-xl">
            Record every trade. Add rows as you trade through the quarter.
          </p>
        </div>
        {editing && (
          <button
            type="button"
            onClick={addRow}
            className="shrink-0 rounded-xl bg-black dark:bg-white px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all"
          >
            + Add row
          </button>
        )}
      </header>
      <div className="overflow-x-auto -mx-1 px-1">
        <table className="w-full border-collapse text-[11px]">
          <thead>
            <tr className="text-left text-[10px] font-black uppercase tracking-[0.2em] text-black/20 dark:text-white/20">
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  className={`${c.width} border-b border-black/5 dark:border-white/5 px-3 py-3 font-black`}
                >
                  {c.label}
                </th>
              ))}
              {editing && <th className="w-12 border-b border-black/5 dark:border-white/5" aria-label="actions" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-black/5 dark:divide-white/5">
            {value.length === 0 && (
              <tr>
                <td
                  colSpan={editing ? COLUMNS.length + 1 : COLUMNS.length}
                  className="py-12 text-center text-black/30 dark:text-white/30 font-bold italic"
                >
                  No journal rows yet. {editing ? 'Click + Add row to start.' : ''}
                </td>
              </tr>
            )}
            {value.map((row, idx) => (
              <tr key={idx} className="group hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors">
                {COLUMNS.map((c) => (
                  <td key={c.key} className="px-1 py-1.5">
                    {editing ? (
                      <input
                        type="text"
                        value={row[c.key]}
                        onChange={(e) => setCell(idx, c.key, e.target.value)}
                        className="w-full rounded border border-transparent bg-white dark:bg-black px-2 py-1.5 text-[11px] font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
                        aria-label={`${c.label} row ${idx + 1}`}
                      />
                    ) : (
                      <span className="block px-2 py-1.5 font-bold text-black dark:text-white tracking-tight">
                        {row[c.key] || '—'}
                      </span>
                    )}
                  </td>
                ))}
                {editing && (
                  <td className="px-1 text-center">
                    <button
                      type="button"
                      onClick={() => removeRow(idx)}
                      className="rounded-lg p-2 text-black/20 dark:text-white/20 hover:text-red-500 hover:bg-red-500/10 transition-all font-black text-sm"
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
