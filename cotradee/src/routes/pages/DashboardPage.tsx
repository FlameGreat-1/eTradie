import { useEffect, useState } from 'react';
import { useExecutionState } from '@/features/execution/api/brokerAccount';
import { useLatestAnalysis, useAnalysisStats } from '@/features/analysis/api/analysis';
import { useSymbols } from '@/features/symbols/api/symbols';
import { useLiveReasoningStream } from '@/features/alerts/hooks/useLiveReasoningStream';
import { formatCurrency, formatPercentage, formatRelativeTime } from '@/utils/formatters';
import { Zap, TrendingUp, BarChart3, Activity, ChevronDown, ChevronUp } from 'lucide-react';

/**
 * Dashboard home page.
 *
 * Renders four metric cards, the recent-analysis feed (3 rows), and a
 * live-reasoning panel that appears at the top of the feed whenever
 * the user's engine is mid-cycle. The live panel auto-closes on
 * `final`/`error` and triggers a feed refetch so the latest analysis
 * slides into the top slot seamlessly.
 */
export default function DashboardPage() {
  const { data: execState } = useExecutionState();
  const { data: latest, refetch: refetchLatest } = useLatestAnalysis(10);
  const { data: stats } = useAnalysisStats();
  const { data: symbolData } = useSymbols();

  const analyses = latest?.analyses ?? [];
  const recentThree = analyses.slice(0, 3);

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [lastTopId, setLastTopId] = useState<string | null>(null);

  // Live reasoning stream. The hook owns connection lifecycle, auth,
  // reconnect/backoff, and terminal-frame semantics. We only care
  // about the state it produces.
  const stream = useLiveReasoningStream(() => {
    void refetchLatest();
  });

  // Auto-expand the newest completed analysis as it arrives, but
  // don't steal focus from the live stream while it is running.
  useEffect(() => {
    if (recentThree.length > 0 && !stream.isStreaming) {
      const currentTopId = String(recentThree[0].analysis_id);
      if (currentTopId !== lastTopId) {
        setLastTopId(currentTopId);
        setExpandedId(currentTopId);
      }
    }
  }, [recentThree, lastTopId, stream.isStreaming]);

  // While streaming, keep the live row expanded so the user sees the
  // tokens appear. Once the stream ends the effect above takes over.
  useEffect(() => {
    if (stream.isStreaming) {
      setExpandedId('stream_active');
    }
  }, [stream.isStreaming]);

  const streamSymbol = stream.symbol ?? '—';

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-content tracking-tight">Dashboard</h1>
        <span className="text-xs font-medium text-content-muted bg-surface-2 px-2.5 py-1 rounded-md border border-border">
          {symbolData?.symbols?.length ?? 0} symbols active
        </span>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={<Activity size={18} />}
          label="Open Positions"
          value={String(execState?.open_position_count ?? 0)}
        />
        <MetricCard
          icon={<Zap size={18} />}
          label="Pending Orders"
          value={String(execState?.pending_order_count ?? 0)}
        />
        <MetricCard
          icon={<TrendingUp size={18} />}
          label="Daily P&L"
          value={execState ? formatCurrency(execState.daily_realized_pnl) : '---'}
          valueClass={
            execState && execState.daily_realized_pnl >= 0 ? 'text-success' : 'text-danger'
          }
        />
        <MetricCard
          icon={<BarChart3 size={18} />}
          label="Win Rate"
          value={stats?.win_rate != null ? formatPercentage(stats.win_rate) : '---'}
        />
      </div>

      {/* Recent Analysis */}
      <section>
        <h2 className="text-sm font-semibold text-content mb-3 uppercase tracking-wider">
          New Analysis
        </h2>
        <div className="rounded-xl border border-border bg-surface-1 overflow-hidden transition-all duration-300">
          {/* Live Stream Row */}
          {stream.isStreaming && (
            <div className="border-b border-border bg-brand/5 relative overflow-hidden">
              <div className="absolute top-0 left-0 h-0.5 bg-brand animate-pulse w-full" />
              <button
                onClick={() =>
                  setExpandedId(expandedId === 'stream_active' ? null : 'stream_active')
                }
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-2 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xs font-bold text-brand uppercase">{streamSymbol}</span>
                  <span className="text-xs font-semibold text-content-secondary uppercase animate-pulse">
                    {stream.status}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-brand animate-pulse">Live...</span>
                  {expandedId === 'stream_active' ? (
                    <ChevronUp size={14} className="text-content-muted" />
                  ) : (
                    <ChevronDown size={14} className="text-content-muted" />
                  )}
                </div>
              </button>

              {expandedId === 'stream_active' && (
                <div className="px-4 pb-4 pt-1 bg-transparent">
                  {stream.error ? (
                    <div className="text-xs text-warning leading-relaxed font-mono relative pl-3 border-l-2 border-warning/50 bg-surface-2 p-3 rounded-r-lg">
                      {stream.error}
                    </div>
                  ) : (
                    <div className="text-xs text-content leading-relaxed font-mono relative pl-3 border-l-2 border-brand bg-surface-2 p-3 rounded-r-lg whitespace-pre-wrap flex flex-col">
                      <span>{stream.reasoning}</span>
                      <span className="w-1.5 h-3 bg-brand animate-pulse inline-block mt-1" />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {recentThree.length === 0 && !stream.isStreaming && (
            <div className="p-8 text-center text-sm text-content-muted">
              No analyses yet. Run a cycle or stream to generate signals.
            </div>
          )}

          {/* Historical Rows */}
          {recentThree.map((a: any, i: number) => {
            const id = String(a.analysis_id ?? i);
            const isExpanded = expandedId === id;
            const reasoningText = a.display?.reasoning || 'No details available.';

            return (
              <div key={id} className="border-b border-border last:border-b-0 group">
                <button
                  onClick={() => setExpandedId(isExpanded ? null : id)}
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-2 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-brand">{String(a.pair ?? '')}</span>
                    <span
                      className={`text-xs font-semibold ${
                        a.direction === 'LONG' || a.direction === 'BUY'
                          ? 'text-success'
                          : a.direction === 'SHORT' || a.direction === 'SELL'
                          ? 'text-danger'
                          : 'text-content-secondary'
                      }`}
                    >
                      {String(a.direction ?? '-')}
                    </span>
                    <span className="text-[10px] text-content-muted px-1.5 py-0.5 rounded bg-surface-2 border border-border">
                      {String(a.setup_grade ?? '-')}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] text-content-muted">
                      {a.created_at ? formatRelativeTime(String(a.created_at)) : ''}
                    </span>
                    {isExpanded ? (
                      <ChevronUp size={14} className="text-content-muted" />
                    ) : (
                      <ChevronDown
                        size={14}
                        className="text-content-muted opacity-0 group-hover:opacity-100 transition-opacity"
                      />
                    )}
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 pt-1 bg-surface-1">
                    <div className="text-xs text-brand/90 leading-relaxed font-mono relative pl-3 border-l-2 border-brand/30 bg-surface-2/50 p-3 rounded-r-lg">
                      <span className="whitespace-pre-wrap">{reasoningText}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  valueClass = 'text-content',
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface-1 p-4 flex items-start gap-3">
      <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-brand/10 text-brand flex-shrink-0">
        {icon}
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="text-[10px] font-medium text-content-muted uppercase tracking-wide">
          {label}
        </span>
        <span className={`text-lg font-bold ${valueClass}`}>{value}</span>
      </div>
    </div>
  );
}
