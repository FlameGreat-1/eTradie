import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  useLatestAnalysis,
  useAnalysisHistory,
  useRerunAnalysis,
} from '@/features/analysis/api/analysis';
import { formatRelativeTime } from '@/utils/formatters';
import { RefreshCw, ChevronLeft, ChevronRight, ChevronDown } from 'lucide-react';
import AnalysisDetailModal from '@/features/analysis/components/AnalysisDetailModal';
import AnalysisCountdown from '@/components/ui/AnalysisCountdown';

const PAGE_SIZE = 15;

type AnalysisRow = {
  analysis_id?: string;
  pair?: string;
  direction?: string;
  setup_grade?: string;
  status?: string;
  trading_style?: string;
  created_at?: string;
};

export default function AnalysisPage() {
  const { data: latest, isLoading } = useLatestAnalysis(200);
  const { data: history } = useAnalysisHistory();
  const rerun = useRerunAnalysis();
  const [searchParams, setSearchParams] = useSearchParams();
  const [rerunSymbol, setRerunSymbol] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(searchParams.get('id'));
  const [page, setPage] = useState(1);

  useEffect(() => {
    const id = searchParams.get('id');
    if (id) setSelectedId(id);
  }, [searchParams]);

  const handleCloseModal = () => {
    setSelectedId(null);
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.delete('id');
        return next;
      },
      { replace: true },
    );
  };

  const analyses: AnalysisRow[] = latest?.analyses ?? history?.analyses ?? [];
  const totalPages = Math.max(1, Math.ceil(analyses.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const startIdx = (currentPage - 1) * PAGE_SIZE;
  const pageItems = analyses.slice(startIdx, startIdx + PAGE_SIZE);

  const handleRerun = () => {
    if (rerunSymbol.trim()) rerun.mutate(rerunSymbol.trim());
  };

  return (
    <div className="p-4 sm:p-6 space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h1 className="text-xl font-black tracking-tight text-content">Analysis History</h1>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={rerunSymbol}
            onChange={(e) => setRerunSymbol(e.target.value)}
            placeholder="AUDUSDm"
            className="rounded-2xl border border-border bg-white dark:bg-black px-4 py-2 text-xs font-bold text-content
                       placeholder:text-content-muted focus:border-brand focus:outline-none w-36 shadow-sm focus-ring"
          />
          <button
            onClick={handleRerun}
            disabled={rerun.isPending || !rerunSymbol.trim()}
            className="flex items-center gap-2 rounded-2xl bg-white dark:bg-black border border-brand px-4 py-2 text-xs font-bold text-brand
                       hover:bg-brand/5 disabled:opacity-50 transition-all duration-fast shadow-sm focus-ring"
          >
            <RefreshCw size={14} className={rerun.isPending ? 'animate-spin' : ''} />
            Re-analyze
          </button>
        </div>
      </div>

      {/* Free tier countdown timer */}
      <AnalysisCountdown />

      {/* Desktop grid */}
      <div className="hidden md:block rounded-2xl border border-border bg-white dark:bg-black overflow-hidden shadow-sm">
        <div className="grid grid-cols-[1fr_1fr_1fr_1fr_1fr_1fr_auto] gap-4 items-center px-5 py-3 border-b border-border bg-surface-1
                        text-[11px] font-bold text-content-muted tracking-tight">
          <span>Pair</span>
          <span>Direction</span>
          <span>Grade</span>
          <span>Status</span>
          <span>Style</span>
          <span className="text-right">Time</span>
          <span className="sr-only">Open</span>
        </div>

        {isLoading && (
          <div className="p-6 space-y-2">
            <div className="h-3 skeleton w-full" />
            <div className="h-3 skeleton w-5/6" />
            <div className="h-3 skeleton w-4/6" />
          </div>
        )}
        {!isLoading && analyses.length === 0 && (
          <div className="p-8 text-center text-sm text-content-muted">
            No analysis records found.
          </div>
        )}
        {pageItems.map((a, i) => {
          const id = String(a.analysis_id ?? '');
          const dir = String(a.direction ?? '-');
          const isLong = dir === 'LONG' || dir === 'BUY';
          const isOpen = selectedId === id && !!id;
          return (
            <div
              key={id || i}
              onClick={() => id && setSelectedId(id)}
              className="grid grid-cols-[1fr_1fr_1fr_1fr_1fr_1fr_auto] gap-4 items-center px-5 py-4 border-b border-border last:border-b-0
                         hover:bg-surface-1 transition-all duration-fast text-xs cursor-pointer group"
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (id && (e.key === 'Enter' || e.key === ' ')) setSelectedId(id);
              }}
            >
              <span className="font-black text-brand truncate tracking-tight">{String(a.pair ?? '')}</span>
              <span className={isLong ? 'text-success font-bold' : 'text-danger font-bold'}>
                {dir}
              </span>
              <span className="font-bold text-content">{String(a.setup_grade ?? '-')}</span>
              <span
                className={`font-bold ${
                  a.status === 'success'
                    ? 'text-success'
                    : 'text-content-muted'
                }`}
              >
                {String(a.status ?? '-')}
              </span>
              <span className="text-content-muted font-medium truncate">{String(a.trading_style ?? '')}</span>
              <span className="text-right text-content-muted font-medium">
                {a.created_at ? formatRelativeTime(String(a.created_at)) : ''}
              </span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (id) setSelectedId(id);
                  }}
                  disabled={!id}
                  aria-expanded={isOpen}
                  aria-label={isOpen ? 'Close analysis details' : 'Open analysis details'}
                  className={`shrink-0 w-8 h-8 flex items-center justify-center rounded-2xl
                              transition-all duration-300 focus-ring border
                              ${
                                isOpen
                                  ? 'bg-transparent border-brand text-brand'
                                  : 'bg-surface-2 border-transparent text-content-muted group-hover:bg-surface-3'
                              }`}
                >
                  <ChevronDown size={14} strokeWidth={2.5} className={isOpen ? 'rotate-180' : ''} />
                </button>
            </div>
          );
        })}
      </div>

      {/* Mobile card list */}
      <div className="md:hidden space-y-2">
        {isLoading && (
          <div className="rounded-xl border border-border bg-surface-1 p-4">
            <div className="h-3 skeleton w-1/2 mb-2" />
            <div className="h-3 skeleton w-3/4" />
          </div>
        )}
        {!isLoading && analyses.length === 0 && (
          <div className="rounded-xl border border-border bg-surface-1 p-6 text-center text-xs text-content-muted">
            No analysis records found.
          </div>
        )}
        {pageItems.map((a, i) => {
          const id = String(a.analysis_id ?? '');
          const dir = String(a.direction ?? '-');
          const isLong = dir === 'LONG' || dir === 'BUY';
          const isOpen = selectedId === id && !!id;
          return (
            <div
              key={id || i}
              role="button"
              tabIndex={0}
              onClick={() => id && setSelectedId(id)}
              onKeyDown={(e) => {
                if (id && (e.key === 'Enter' || e.key === ' ')) setSelectedId(id);
              }}
              className="w-full text-left rounded-2xl border border-border bg-white dark:bg-black p-4 hover:bg-surface-1
                         transition-all duration-fast focus-ring cursor-pointer shadow-sm"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-bold text-brand text-sm">{a.pair ?? ''}</span>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wide ${
                      isLong ? 'text-success' : 'text-danger'
                    }`}
                  >
                    {dir}
                  </span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (id) setSelectedId(id);
                      }}
                      disabled={!id}
                      aria-expanded={isOpen}
                      aria-label={isOpen ? 'Close analysis details' : 'Open analysis details'}
                      className={`shrink-0 w-8 h-8 flex items-center justify-center rounded-2xl
                                  transition-all duration-300 focus-ring border
                                  ${
                                    isOpen
                                      ? 'bg-transparent border-brand text-brand'
                                      : 'bg-surface-1 border-transparent text-content-muted'
                                  }`}
                    >
                      <ChevronDown size={14} strokeWidth={2.5} className={isOpen ? 'rotate-180' : ''} />
                    </button>
                </div>
              </div>
              <div className="mt-1.5 grid grid-cols-3 gap-2 text-[11px]">
                <Field label="Grade" value={a.setup_grade ?? '—'} />
                <Field
                  label="Status"
                  value={a.status ?? '—'}
                  valueClass={
                    a.status === 'success'
                      ? 'text-success'
                      : a.status === 'no_setup'
                      ? 'text-content-muted'
                      : 'text-content-muted'
                  }
                />
                <Field label="Style" value={a.trading_style ?? '—'} />
              </div>
              <div className="mt-2 text-[10px] text-content-muted">
                {a.created_at ? formatRelativeTime(String(a.created_at)) : ''}
              </div>
            </div>
          );
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pt-1">
          <span className="text-xs text-content-muted">
            Showing {startIdx + 1}–{Math.min(startIdx + PAGE_SIZE, analyses.length)} of{' '}
            {analyses.length} analyses
          </span>
          <div className="flex items-center gap-1 self-end sm:self-auto">
            <PageBtn
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              aria-label="Previous page"
            >
              <ChevronLeft size={14} />
            </PageBtn>
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter(
                (p) => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1,
              )
              .reduce<(number | 'dot')[]>((acc, p, idx, arr) => {
                if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push('dot');
                acc.push(p);
                return acc;
              }, [])
              .map((item, idx) =>
                item === 'dot' ? (
                  <span
                    key={`dot-${idx}`}
                    className="px-1 text-xs text-content-muted select-none"
                  >
                    …
                  </span>
                ) : (
                  <button
                    key={item}
                    onClick={() => setPage(item as number)}
                    className={`flex items-center justify-center w-8 h-8 rounded-2xl text-xs font-bold transition-all duration-fast focus-ring
                                ${
                                  currentPage === item
                                    ? 'bg-brand text-white border border-brand shadow-sm'
                                    : 'border border-border bg-white dark:bg-black text-content-muted hover:bg-surface-2 hover:text-content'
                                }`}
                  >
                    {item}
                  </button>
                ),
              )}
            <PageBtn
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              aria-label="Next page"
            >
              <ChevronRight size={14} />
            </PageBtn>
          </div>
        </div>
      )}

      {selectedId && (
        <AnalysisDetailModal analysisId={selectedId} onClose={handleCloseModal} />
      )}
    </div>
  );
}

function PageBtn({
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className="flex items-center justify-center w-8 h-8 rounded-2xl border border-border bg-white dark:bg-black
                 text-content-muted hover:bg-surface-2 hover:text-content disabled:opacity-30
                 disabled:cursor-not-allowed transition-all duration-fast focus-ring shadow-sm"
    >
      {children}
    </button>
  );
}

function Field({
  label,
  value,
  valueClass = 'text-content',
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex flex-col gap-0.5 min-w-0">
      <span className="text-[10px] font-bold text-content-muted truncate">
        {label}
      </span>
      <span className={`font-black text-xs truncate ${valueClass}`}>{value}</span>
    </div>
  );
}
