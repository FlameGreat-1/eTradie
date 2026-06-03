import { useCallback, useMemo, useState } from 'react';
import type { JournalRow } from '../../types';
import { useTradingPlanJournalHistory } from '../../api/hooks';

interface Props {
  value: JournalRow[];
  editing: boolean;
  onChange: (next: JournalRow[]) => void;
  headerActions?: React.ReactNode;
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
 * The live table shows the CURRENT rolling 90-day window of
 * auto-filled + hand-typed rows (the plan blob). Older auto rows roll
 * out of the blob as the window advances; the read-only "Past windows"
 * panel pages back through those PREVIOUS windows straight from the
 * permanent management_trades record so nothing is ever lost.
 *
 * Add/remove affordances are surfaced only in edit mode.
 */
export function JournalSection({ value, editing, onChange, headerActions }: Props) {
  const [showHistory, setShowHistory] = useState(false);

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
      <header className="mb-4 flex items-start justify-between gap-2 sm:gap-4">
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 mb-1">Section 03</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Daily Execution Journal</h3>
          <p className="mt-1 text-[10px] sm:text-xs font-medium text-black/40 dark:text-white/40 leading-relaxed max-w-xl">
            Record every trade. Add rows as you trade through the quarter.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {headerActions}
          {!editing && (
            <button
              type="button"
              onClick={() => setShowHistory((s) => !s)}
              aria-pressed={showHistory}
              className={`rounded-xl border px-3 sm:px-5 py-2.5 text-[9px] sm:text-[10px] font-black uppercase tracking-widest transition-all ${
                showHistory
                  ? 'border-black/30 dark:border-white/30 bg-black/[0.04] dark:bg-white/[0.06] text-black dark:text-white'
                  : 'border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white hover:border-black/30 dark:hover:border-white/30'
              }`}
            >
              <span className="sm:hidden">History</span>
              <span className="hidden sm:inline">{showHistory ? 'Hide past windows' : 'Past windows'}</span>
            </button>
          )}
          {editing && (
            <button
              type="button"
              onClick={addRow}
              className="rounded-xl bg-black dark:bg-white px-3 sm:px-5 py-2.5 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all"
            >
              <span className="sm:hidden">+ Row</span>
              <span className="hidden sm:inline">+ Add row</span>
            </button>
          )}
        </div>
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
                        {row[c.key] || '\u2014'}
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
                      \u00d7
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!editing && showHistory && <JournalHistoryPanel />}
    </section>
  );
}

// windowRangeLabel renders a human description of which 90-day window
// is being viewed, e.g. window=0 -> "Current 90 days", window=1 ->
// "91\u2013180 days ago". Mirrors the gateway's journalWindowBounds:
// window N spans [now-(N+1)*days, now-N*days].
function windowRangeLabel(window: number, windowDays: number): string {
  if (window <= 0) return `Current ${windowDays} days`;
  const from = window * windowDays + 1;
  const to = (window + 1) * windowDays;
  return `${from}\u2013${to} days ago`;
}

/**
 * Read-only page-back viewer for PREVIOUS 90-day journal windows.
 *
 * Renders history rows with the SAME COLUMNS list as the live table
 * (so a past-window row is byte-identical, and the hidden trade_id is
 * excluded exactly as it is in the live table and the Excel export).
 * Window navigation steps older/newer; page navigation walks the
 * closed set within a window. Local state only \u2014 it never touches the
 * parent's draft / edit flow.
 */
function JournalHistoryPanel() {
  const [window, setWindow] = useState(1); // start at the previous window
  const [page, setPage] = useState(0);

  const { data, isLoading, isError, isFetching } = useTradingPlanJournalHistory(window, page);

  const windowDays = data?.window_days ?? 90;
  const rows = data?.rows ?? [];
  const hasMore = data?.has_more ?? false;
  const totalClosed = data?.total_closed ?? 0;

  const goOlderWindow = useCallback(() => {
    setWindow((w) => w + 1);
    setPage(0);
  }, []);
  const goNewerWindow = useCallback(() => {
    setWindow((w) => Math.max(0, w - 1));
    setPage(0);
  }, []);
  const goPrevPage = useCallback(() => setPage((p) => Math.max(0, p - 1)), []);
  const goNextPage = useCallback(() => setPage((p) => p + 1), []);

  const rangeLabel = useMemo(() => windowRangeLabel(window, windowDays), [window, windowDays]);

  return (
    <div className="mt-6 rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.03] p-4 sm:p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 mb-1">Past windows</div>
          <div className="text-sm font-bold text-black dark:text-white tracking-tight">{rangeLabel}</div>
          <div className="mt-0.5 text-[10px] font-medium text-black/40 dark:text-white/40">
            {totalClosed} closed {totalClosed === 1 ? 'trade' : 'trades'} in this window
            {isFetching && ' \u00b7 updating\u2026'}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={goNewerWindow}
            disabled={window <= 1}
            className="rounded-lg border border-black/10 dark:border-white/10 bg-white/40 dark:bg-black/40 px-3 py-2 text-[9px] font-black uppercase tracking-widest text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white hover:border-black/30 dark:hover:border-white/30 transition-all disabled:opacity-20"
          >
            \u2190 Newer
          </button>
          <button
            type="button"
            onClick={goOlderWindow}
            className="rounded-lg border border-black/10 dark:border-white/10 bg-white/40 dark:bg-black/40 px-3 py-2 text-[9px] font-black uppercase tracking-widest text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white hover:border-black/30 dark:hover:border-white/30 transition-all"
          >
            Older \u2192
          </button>
        </div>
      </div>

      {isError ? (
        <div className="py-10 text-center text-[11px] font-bold italic text-red-500/70">
          Could not load journal history. Please try again in a moment.
        </div>
      ) : isLoading ? (
        <div className="py-10 text-center text-[11px] font-bold italic text-black/30 dark:text-white/30">
          Loading\u2026
        </div>
      ) : (
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
              </tr>
            </thead>
            <tbody className="divide-y divide-black/5 dark:divide-white/5">
              {rows.length === 0 && (
                <tr>
                  <td
                    colSpan={COLUMNS.length}
                    className="py-10 text-center text-black/30 dark:text-white/30 font-bold italic"
                  >
                    No trades recorded in this window.
                  </td>
                </tr>
              )}
              {rows.map((row, idx) => (
                <tr key={idx} className="hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors">
                  {COLUMNS.map((c) => (
                    <td key={c.key} className="px-1 py-1.5">
                      <span className="block px-2 py-1.5 font-bold text-black dark:text-white tracking-tight">
                        {row[c.key] || '\u2014'}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={goPrevPage}
          disabled={page <= 0}
          className="rounded-lg border border-black/10 dark:border-white/10 bg-white/40 dark:bg-black/40 px-3 py-2 text-[9px] font-black uppercase tracking-widest text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white hover:border-black/30 dark:hover:border-white/30 transition-all disabled:opacity-20"
        >
          \u2190 Prev page
        </button>
        <span className="text-[10px] font-black uppercase tracking-widest text-black/30 dark:text-white/30">
          Page {page + 1}
        </span>
        <button
          type="button"
          onClick={goNextPage}
          disabled={!hasMore}
          className="rounded-lg border border-black/10 dark:border-white/10 bg-white/40 dark:bg-black/40 px-3 py-2 text-[9px] font-black uppercase tracking-widest text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white hover:border-black/30 dark:hover:border-white/30 transition-all disabled:opacity-20"
        >
          Next page \u2192
        </button>
      </div>
    </div>
  );
}
