import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from '@/hooks/useToast';
import { LogoLoader } from '@/components/ui/LogoLoader';
import {
  downloadJournalAsExcel,
  useTradingPlanJournal,
  useUpsertJournalAnnotation,
  type CompositeJournalRow,
  type JournalAnnotation,
  type JournalWindow,
} from '../..';

// Objective columns: read-only, formatted by the gateway (design §7).
// Close cells (exit / rr_achieved / pnl / outcome) are intentionally
// blank while the trade is open.
const OBJECTIVE_COLUMNS: Array<{ key: keyof CompositeJournalRow; label: string; width: string }> = [
  { key: 'date',          label: 'Date',          width: 'w-32'  },
  { key: 'session',       label: 'Session',       width: 'w-24'  },
  { key: 'pair',          label: 'Pair',          width: 'w-20'  },
  { key: 'direction',     label: 'Direction',     width: 'w-20'  },
  { key: 'style',         label: 'Style',         width: 'w-24'  },
  { key: 'setup_type',    label: 'Setup Type',    width: 'w-28'  },
  { key: 'entry',         label: 'Entry',         width: 'w-24'  },
  { key: 'stop_loss',     label: 'Stop Loss',     width: 'w-24'  },
  { key: 'take_profit',   label: 'Take Profit',   width: 'w-32'  },
  { key: 'risk_percent',  label: 'Risk %',        width: 'w-20'  },
  { key: 'position_size', label: 'Position Size', width: 'w-28'  },
  { key: 'exit',          label: 'Exit',          width: 'w-24'  },
  { key: 'rr_planned',    label: 'RR Planned',    width: 'w-24'  },
  { key: 'rr_achieved',   label: 'RR Achieved',   width: 'w-24'  },
  { key: 'pnl',           label: 'P&L',           width: 'w-28'  },
  { key: 'outcome',       label: 'Outcome',       width: 'w-20'  },
];

// Subjective columns: editable, persisted as a JournalAnnotation keyed
// by trade_id. These are the entire point of the workbook.
const SUBJECTIVE_COLUMNS: Array<{ key: keyof JournalAnnotation; label: string; width: string }> = [
  { key: 'htf_bias',             label: 'HTF Bias',             width: 'w-28'           },
  { key: 'rule_followed',        label: 'Rule Followed?',       width: 'w-28'           },
  { key: 'emotion_before_trade', label: 'Emotion Before Trade', width: 'w-36'           },
  { key: 'emotion_after_trade',  label: 'Emotion After Trade',  width: 'w-36'           },
  { key: 'trade_quality',        label: 'Trade Quality',        width: 'w-24'           },
  { key: 'mistake_category',     label: 'Mistake Category',     width: 'w-36'           },
  { key: 'news_present',         label: 'News Present?',        width: 'w-28'           },
  { key: 'screenshot_link',      label: 'Screenshot Link',      width: 'min-w-[12rem]'  },
  { key: 'notes',                label: 'Notes',                width: 'min-w-[14rem]'  },
];

const SUBJECTIVE_KEYS = SUBJECTIVE_COLUMNS.map((c) => c.key);

// annotationFromRow extracts the subjective fields (+ trade_id) of a
// composite row into the JournalAnnotation upsert shape.
function annotationFromRow(row: CompositeJournalRow): JournalAnnotation {
  return {
    trade_id: row.trade_id,
    htf_bias: row.htf_bias,
    rule_followed: row.rule_followed,
    emotion_before_trade: row.emotion_before_trade,
    emotion_after_trade: row.emotion_after_trade,
    trade_quality: row.trade_quality,
    mistake_category: row.mistake_category,
    news_present: row.news_present,
    screenshot_link: row.screenshot_link,
    notes: row.notes,
  };
}

interface Props {
  headerActions?: React.ReactNode;
}

/**
 * Section 3 — Daily Execution Journal (auto-populated, manual trades).
 *
 * A COMPOSITE view: objective trade facts are read live from the
 * management service (the moment a manual trade is reconciled a row
 * appears; it completes through to close), and the trader fills only
 * the subjective columns, which persist by trade_id in the plan.
 *
 * The objective cells are never editable (one-way sink: management ->
 * view, never view -> execution). The subjective cells save on blur.
 */
export function AutoJournalSection({ headerActions }: Props) {
  const [window, setWindow] = useState<JournalWindow>('current');
  const { data, isLoading, isError, refetch, isFetching, dataUpdatedAt } =
    useTradingPlanJournal(window);
  const upsert = useUpsertJournalAnnotation();

  // Local edit buffer for subjective cells, keyed by trade_id. Seeded
  // from the server rows and updated as the trader types; saved on blur.
  const [drafts, setDrafts] = useState<Record<string, JournalAnnotation>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  const rows = useMemo(() => data?.rows ?? [], [data?.rows]);

  // Re-seed the local buffer whenever the server rows change (window
  // switch, refetch, annotation invalidation). The trader's in-flight
  // keystrokes are preserved for rows that already have a draft.
  useEffect(() => {
    setDrafts((prev) => {
      const next: Record<string, JournalAnnotation> = {};
      for (const r of rows) {
        next[r.trade_id] = prev[r.trade_id] ?? annotationFromRow(r);
      }
      return next;
    });
  }, [rows]);

  const setCell = useCallback(
    (tradeID: string, key: keyof JournalAnnotation, value: string) => {
      setDrafts((prev) => ({
        ...prev,
        [tradeID]: { ...prev[tradeID], trade_id: tradeID, [key]: value },
      }));
    },
    [],
  );

  // Commit a row's annotation on blur, but only when it actually
  // differs from what the server returned (avoids a needless PUT on
  // focus-through).
  const commit = useCallback(
    (row: CompositeJournalRow) => {
      const draft = drafts[row.trade_id];
      if (!draft) return;
      const server = annotationFromRow(row);
      const dirty = SUBJECTIVE_KEYS.some((k) => (draft[k] ?? '') !== (server[k] ?? ''));
      if (!dirty) return;
      setSavingId(row.trade_id);
      upsert.mutate(draft, {
        onSuccess: () => {
          toast({ title: 'Saved', description: 'Journal note saved.', variant: 'success' });
        },
        onError: () => {
          toast({
            title: 'Could not save note',
            description: 'Please try again in a moment.',
            variant: 'destructive',
          });
        },
        onSettled: () => setSavingId((cur) => (cur === row.trade_id ? null : cur)),
      });
    },
    [drafts, upsert],
  );

  const handleExport = useCallback(() => {
    if (rows.length === 0) return;
    const name = downloadJournalAsExcel(rows);
    toast({ title: 'Journal exported', description: `Saved as ${name}.`, variant: 'success' });
  }, [rows]);

  const lastSynced = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : '';
  const totalCols = OBJECTIVE_COLUMNS.length + SUBJECTIVE_COLUMNS.length + 1; // +1 status

  return (
    <section className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm overflow-hidden transition-all duration-300">
      <header className="mb-4 flex flex-wrap items-start justify-between gap-2 sm:gap-4">
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 mb-1">Section 03</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Daily Execution Journal</h3>
          <p className="mt-1 text-[10px] sm:text-xs font-medium text-black/40 dark:text-white/40 leading-relaxed max-w-xl">
            Your manual trades populate here automatically as you trade. Fill in the
            subjective columns — the objective facts are synced from your account.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          {headerActions}
          {/* Window selector */}
          <div className="flex items-center gap-1 bg-black/5 dark:bg-white/5 p-1 rounded-xl border border-black/5 dark:border-white/5">
            {(['current', 'previous'] as JournalWindow[]).map((w) => {
              const active = window === w;
              return (
                <button
                  key={w}
                  type="button"
                  onClick={() => setWindow(w)}
                  className={`rounded-lg px-3 py-1.5 text-[9px] sm:text-[10px] font-black uppercase tracking-wider transition-all ${
                    active
                      ? 'bg-black dark:bg-white text-white dark:text-black shadow-sm'
                      : 'text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white'
                  }`}
                >
                  {w === 'current' ? 'Current 90d' : 'Previous 90d'}
                </button>
              );
            })}
          </div>
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="rounded-xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] px-3 py-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white hover:border-black/30 dark:hover:border-white/30 transition-all disabled:opacity-30"
          >
            {isFetching ? 'Syncing…' : 'Refresh'}
          </button>
          <button
            type="button"
            onClick={handleExport}
            disabled={rows.length === 0}
            className="rounded-xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] px-3 py-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white hover:border-black/30 dark:hover:border-white/30 transition-all disabled:opacity-30"
          >
            Export Excel
          </button>
        </div>
      </header>

      {lastSynced && !isLoading && !isError && (
        <div className="mb-3 text-[9px] font-bold uppercase tracking-widest text-black/30 dark:text-white/30">
          Synced {lastSynced}
          {typeof data?.total_closed === 'number' && (
            <span> · {data.total_closed} closed in window</span>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <LogoLoader size={40} />
        </div>
      ) : isError ? (
        <div className="py-12 text-center text-black/40 dark:text-white/40 font-bold">
          The trade journal is temporarily unavailable. Please try Refresh in a moment.
        </div>
      ) : (
        <div className="overflow-x-auto -mx-1 px-1">
          <table className="w-full border-collapse text-[11px]">
            <thead>
              <tr className="text-left text-[10px] font-black uppercase tracking-[0.2em] text-black/20 dark:text-white/20">
                <th className="w-20 border-b border-black/5 dark:border-white/5 px-3 py-3 font-black">Status</th>
                {OBJECTIVE_COLUMNS.map((c) => (
                  <th key={c.key} className={`${c.width} border-b border-black/5 dark:border-white/5 px-3 py-3 font-black`}>
                    {c.label}
                  </th>
                ))}
                {SUBJECTIVE_COLUMNS.map((c) => (
                  <th key={c.key} className={`${c.width} border-b border-black/5 dark:border-white/5 px-3 py-3 font-black text-brand`}>
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-black/5 dark:divide-white/5">
              {rows.length === 0 && (
                <tr>
                  <td colSpan={totalCols} className="py-12 text-center text-black/30 dark:text-white/30 font-bold italic">
                    No manual trades in this window yet. Trades you place by hand appear here automatically.
                  </td>
                </tr>
              )}
              {rows.map((row) => {
                const draft = drafts[row.trade_id] ?? annotationFromRow(row);
                const saving = savingId === row.trade_id;
                return (
                  <tr key={row.trade_id} className="group hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors">
                    {/* Status badge */}
                    <td className="px-3 py-1.5">
                      {row.is_open ? (
                        <span className="inline-block rounded-full bg-amber-500/10 px-2 py-0.5 text-[8px] font-black uppercase tracking-widest text-amber-500">
                          Open
                        </span>
                      ) : (
                        <span className="inline-block rounded-full bg-emerald-500/10 px-2 py-0.5 text-[8px] font-black uppercase tracking-widest text-emerald-500">
                          Synced
                        </span>
                      )}
                    </td>

                    {/* Objective cells — read-only */}
                    {OBJECTIVE_COLUMNS.map((c) => (
                      <td key={c.key} className="px-1 py-1.5">
                        <span className="block px-2 py-1.5 font-bold text-black dark:text-white tracking-tight">
                          {String(row[c.key] ?? '') || (row.is_open ? '—' : '—')}
                        </span>
                      </td>
                    ))}

                    {/* Subjective cells — editable */}
                    {SUBJECTIVE_COLUMNS.map((c) => (
                      <td key={c.key} className="px-1 py-1.5">
                        <input
                          type="text"
                          value={draft[c.key] ?? ''}
                          onChange={(e) => setCell(row.trade_id, c.key, e.target.value)}
                          onBlur={() => commit(row)}
                          disabled={saving}
                          className="w-full rounded border border-transparent bg-white dark:bg-black px-2 py-1.5 text-[11px] font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none disabled:opacity-50"
                          aria-label={`${c.label} for trade ${row.pair || row.trade_id}`}
                        />
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
