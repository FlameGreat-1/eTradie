import { useState } from 'react';
import { ChevronLeft, ChevronRight, ChevronsRight, Loader2 } from 'lucide-react';
import {
  usePerformanceReviewById,
  usePerformanceReviewHistory,
} from '../api/hooks';
import type { PerformanceReviewHistoryRow, PerformanceReviewPeriod } from '../types';
import { PerformanceReviewSections } from './PerformanceReviewSections';

/**
 * History tab. Lists every previously generated review (weekly and
 * monthly) paginated 20-at-a-time. Clicking a row expands it inline
 * into the full 14-section view by fetching /:id on demand.
 *
 * Responsive: the list is a single column on mobile and a two-pane
 * (list + detail) layout on lg+.
 */
export function PerformanceReviewHistory() {
  const [period, setPeriod] = useState<PerformanceReviewPeriod | 'all'>('all');
  const [offset, setOffset] = useState(0);
  const limit = 20;
  const { data, isLoading } = usePerformanceReviewHistory(
    period === 'all' ? undefined : period,
    offset,
    limit,
  );
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { data: detail, isLoading: detailLoading } = usePerformanceReviewById(selectedId);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasPrev = offset > 0;
  const hasNext = offset + limit < total;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)] gap-4 sm:gap-5">
      <aside className="flex flex-col gap-3">
        <PeriodFilter value={period} onChange={(p) => { setPeriod(p); setOffset(0); setSelectedId(null); }} />

        {isLoading ? (
          <div className="py-12 flex items-center justify-center">
            <Loader2 size={20} className="animate-spin text-black/40 dark:text-white/40" />
          </div>
        ) : items.length === 0 ? (
          <div className="py-12 px-4 text-center text-xs sm:text-sm text-black/50 dark:text-white/50 rounded-2xl border border-dashed border-black/10 dark:border-white/10">
            No reviews yet for this filter.
          </div>
        ) : (
          <ul className="flex flex-col gap-2">
            {items.map((row) => (
              <HistoryRow
                key={row.id}
                row={row}
                active={selectedId === row.id}
                onSelect={setSelectedId}
              />
            ))}
          </ul>
        )}

        {items.length > 0 && (
          <Pagination
            offset={offset}
            limit={limit}
            total={total}
            hasPrev={hasPrev}
            hasNext={hasNext}
            onPrev={() => setOffset(Math.max(0, offset - limit))}
            onNext={() => setOffset(offset + limit)}
          />
        )}
      </aside>

      <div className="min-w-0">
        {selectedId === null ? (
          <div className="hidden lg:flex h-full items-center justify-center text-center px-6 py-12 rounded-2xl border border-dashed border-black/10 dark:border-white/10">
            <p className="text-sm font-medium text-black/40 dark:text-white/40">
              Select a review from the list to view its full report.
            </p>
          </div>
        ) : detailLoading ? (
          <div className="py-12 flex items-center justify-center">
            <Loader2 size={20} className="animate-spin text-black/40 dark:text-white/40" />
          </div>
        ) : detail?.review ? (
          <PerformanceReviewSections review={detail.review} />
        ) : (
          <div className="py-12 px-6 text-center text-sm text-black/50 dark:text-white/50 rounded-2xl border border-dashed border-black/10 dark:border-white/10">
            Could not load review.
          </div>
        )}
      </div>
    </div>
  );
}

function PeriodFilter({
  value,
  onChange,
}: {
  value: PerformanceReviewPeriod | 'all';
  onChange: (v: PerformanceReviewPeriod | 'all') => void;
}) {
  const opts: { id: PerformanceReviewPeriod | 'all'; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'weekly', label: 'Weekly' },
    { id: 'monthly', label: 'Monthly' },
  ];
  return (
    <div className="flex items-center gap-1 p-1 rounded-xl bg-black/[0.03] dark:bg-white/[0.03]">
      {opts.map((o) => {
        const active = o.id === value;
        return (
          <button
            key={o.id}
            type="button"
            onClick={() => onChange(o.id)}
            className={`flex-1 px-2 py-1.5 rounded-lg text-[11px] sm:text-xs font-bold transition-all focus-ring ${
              active
                ? 'bg-white dark:bg-black text-black dark:text-white shadow-sm'
                : 'text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white'
            }`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function HistoryRow({
  row,
  active,
  onSelect,
}: {
  row: PerformanceReviewHistoryRow;
  active: boolean;
  onSelect: (id: number) => void;
}) {
  const startLabel = formatDate(row.period_start);
  const endLabel = formatDate(row.period_end);
  const updatedLabel = formatDate(row.updated_at);
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(row.id)}
        aria-current={active}
        className={`w-full flex items-start justify-between gap-3 px-3 py-3 rounded-xl text-left transition-all focus-ring border ${
          active
            ? 'border-black/20 dark:border-white/20 bg-black/5 dark:bg-white/5'
            : 'border-black/5 dark:border-white/5 hover:bg-black/[0.03] dark:hover:bg-white/[0.03]'
        }`}
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-widest text-black/40 dark:text-white/40">
              {row.period}
            </span>
            <StatusPill status={row.status} />
          </div>
          <p className="mt-1 text-xs sm:text-sm font-bold text-black dark:text-white truncate">
            {startLabel} \u2013 {endLabel}
          </p>
          <p className="text-[11px] text-black/40 dark:text-white/40">Updated {updatedLabel}</p>
        </div>
        <ChevronsRight
          size={14}
          className={`shrink-0 mt-1 ${
            active ? 'text-black/60 dark:text-white/60' : 'text-black/30 dark:text-white/30'
          }`}
          aria-hidden
        />
      </button>
    </li>
  );
}

function StatusPill({ status }: { status: PerformanceReviewHistoryRow['status'] }) {
  const palette: Record<string, string> = {
    ready: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20',
    generating: 'bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/20',
    failed: 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/20',
  };
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded-md border text-[9px] font-bold uppercase tracking-widest ${
        palette[status] ?? 'bg-black/5 dark:bg-white/5 text-black/60 dark:text-white/60 border-black/10 dark:border-white/10'
      }`}
    >
      {status}
    </span>
  );
}

function Pagination({
  offset,
  limit,
  total,
  hasPrev,
  hasNext,
  onPrev,
  onNext,
}: {
  offset: number;
  limit: number;
  total: number;
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
}) {
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div className="flex items-center justify-between gap-3 pt-1">
      <span className="text-[11px] text-black/40 dark:text-white/40">
        {from}\u2013{to} of {total}
      </span>
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={onPrev}
          disabled={!hasPrev}
          aria-label="Previous page"
          className="p-1.5 rounded-md border border-black/5 dark:border-white/5 text-black/60 dark:text-white/60 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-black/5 dark:hover:bg-white/5 focus-ring"
        >
          <ChevronLeft size={14} />
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={!hasNext}
          aria-label="Next page"
          className="p-1.5 rounded-md border border-black/5 dark:border-white/5 text-black/60 dark:text-white/60 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-black/5 dark:hover:bg-white/5 focus-ring"
        >
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

function formatDate(iso?: string): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}
