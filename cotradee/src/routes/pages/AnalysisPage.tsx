import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useLatestAnalysis, useAnalysisHistory, useRerunAnalysis } from '@/features/analysis/api/analysis';
import { formatRelativeTime } from '@/utils/formatters';
import { RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';
import AnalysisDetailModal from '@/features/analysis/components/AnalysisDetailModal';

const PAGE_SIZE = 15;

export default function AnalysisPage() {
  const { data: latest, isLoading } = useLatestAnalysis(200);
  const { data: history } = useAnalysisHistory();
  const rerun = useRerunAnalysis();
  const [searchParams, setSearchParams] = useSearchParams();
  const [rerunSymbol, setRerunSymbol] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(searchParams.get('id'));
  const [page, setPage] = useState(1);

  // Auto-open modal if ID is in URL (deep link)
  useEffect(() => {
    const id = searchParams.get('id');
    if (id) setSelectedId(id);
  }, [searchParams]);

  const handleCloseModal = () => {
    setSelectedId(null);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete('id');
      return next;
    }, { replace: true });
  };

  const analyses = latest?.analyses ?? history?.analyses ?? [];
  const totalPages = Math.max(1, Math.ceil(analyses.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const startIdx = (currentPage - 1) * PAGE_SIZE;
  const pageItems = analyses.slice(startIdx, startIdx + PAGE_SIZE);

  const handleRerun = () => {
    if (rerunSymbol.trim()) {
      rerun.mutate(rerunSymbol.trim());
    }
  };

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-content">Analysis History</h1>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={rerunSymbol}
            onChange={(e) => setRerunSymbol(e.target.value)}
            placeholder="AUDUSDm"
            className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs text-content
                       placeholder:text-content-muted focus:border-brand focus:outline-none w-28"
          />
          <button
            onClick={handleRerun}
            disabled={rerun.isPending || !rerunSymbol.trim()}
            className="flex items-center gap-1.5 rounded-lg bg-brand px-3 py-2 text-xs font-semibold text-white
                       hover:bg-brand-dark disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={12} className={rerun.isPending ? 'animate-spin' : ''} />
            Re-analyze
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-surface-1 overflow-hidden">
        <div className="grid grid-cols-6 gap-4 items-center px-4 py-2 border-b border-border bg-surface-2 text-[10px] font-semibold text-content-muted uppercase tracking-wider">
          <span>Pair</span>
          <span>Direction</span>
          <span>Grade</span>
          <span>Status</span>
          <span>Style</span>
          <span className="text-right">Time</span>
        </div>

        {isLoading && (
          <div className="p-8 text-center text-sm text-content-muted">Loading…</div>
        )}
        {!isLoading && analyses.length === 0 && (
          <div className="p-8 text-center text-sm text-content-muted">No analysis records found.</div>
        )}
        {pageItems.map((a: Record<string, unknown>, i: number) => {
          const id = String(a.analysis_id ?? '');
          const dir = String(a.direction ?? '-');
          const isLong = dir === 'LONG' || dir === 'BUY';
          return (
            <div
              key={id || i}
              onClick={() => id && setSelectedId(id)}
              className="grid grid-cols-6 gap-4 items-center px-4 py-3 border-b border-border last:border-b-0
                         hover:bg-surface-2 transition-colors text-xs cursor-pointer"
            >
              <span className="font-bold text-brand">{String(a.pair ?? '')}</span>
              <span className={isLong ? 'text-success font-medium' : 'text-danger font-medium'}>{dir}</span>
              <span className="font-semibold text-content">{String(a.setup_grade ?? '-')}</span>
              <span className={`font-medium ${a.status === 'success' ? 'text-success' : a.status === 'no_setup' ? 'text-warning' : 'text-content-muted'}`}>
                {String(a.status ?? '-')}
              </span>
              <span className="text-content-muted truncate">{String(a.trading_style ?? '')}</span>
              <span className="text-right text-content-muted">
                {a.created_at ? formatRelativeTime(String(a.created_at)) : ''}
              </span>
            </div>
          );
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs text-content-muted">
            Showing {startIdx + 1}–{Math.min(startIdx + PAGE_SIZE, analyses.length)} of {analyses.length} analyses
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="flex items-center justify-center w-8 h-8 rounded-lg border border-border bg-surface-2
                         text-content-muted hover:bg-surface-3 hover:text-content disabled:opacity-30
                         disabled:cursor-not-allowed transition-colors"
              aria-label="Previous page"
            >
              <ChevronLeft size={14} />
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter((p) => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
              .reduce<(number | 'dot')[]>((acc, p, idx, arr) => {
                if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push('dot');
                acc.push(p);
                return acc;
              }, [])
              .map((item, idx) =>
                item === 'dot' ? (
                  <span key={`dot-${idx}`} className="px-1 text-xs text-content-muted select-none">…</span>
                ) : (
                  <button
                    key={item}
                    onClick={() => setPage(item as number)}
                    className={`flex items-center justify-center w-8 h-8 rounded-lg text-xs font-medium transition-colors
                      ${
                        currentPage === item
                          ? 'bg-brand text-white border border-brand'
                          : 'border border-border bg-surface-2 text-content-muted hover:bg-surface-3 hover:text-content'
                      }`}
                  >
                    {item}
                  </button>
                ),
              )}

            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="flex items-center justify-center w-8 h-8 rounded-lg border border-border bg-surface-2
                         text-content-muted hover:bg-surface-3 hover:text-content disabled:opacity-30
                         disabled:cursor-not-allowed transition-colors"
              aria-label="Next page"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selectedId && (
        <AnalysisDetailModal analysisId={selectedId} onClose={handleCloseModal} />
      )}
    </div>
  );
}
