import { useState } from 'react';
import { useLatestAnalysis, useAnalysisHistory, useRerunAnalysis } from '@/features/analysis/api/analysis';
import { formatRelativeTime } from '@/utils/formatters';
import { RefreshCw } from 'lucide-react';
import AnalysisDetailModal from '@/features/analysis/components/AnalysisDetailModal';

export default function AnalysisPage() {
  const { data: latest, isLoading } = useLatestAnalysis(50);
  const { data: history } = useAnalysisHistory();
  const rerun = useRerunAnalysis();
  const [rerunSymbol, setRerunSymbol] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const analyses = latest?.analyses ?? history?.analyses ?? [];

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

      {/* Table Header */}
      <div className="rounded-xl border border-border bg-surface-1 overflow-hidden">
        <div className="grid grid-cols-[100px_80px_60px_80px_1fr_100px] gap-4 items-center px-4 py-2 border-b border-border bg-surface-2 text-[10px] font-semibold text-content-muted uppercase tracking-wider">
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
        {analyses.map((a: Record<string, unknown>, i: number) => {
          const id = String(a.analysis_id ?? '');
          const dir = String(a.direction ?? '-');
          const isLong = dir === 'LONG' || dir === 'BUY';
          return (
            <div
              key={id || i}
              onClick={() => id && setSelectedId(id)}
              className="grid grid-cols-[100px_80px_60px_80px_1fr_100px] gap-4 items-center px-4 py-3 border-b border-border last:border-b-0
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

      {/* Detail Modal */}
      {selectedId && (
        <AnalysisDetailModal analysisId={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </div>
  );
}
