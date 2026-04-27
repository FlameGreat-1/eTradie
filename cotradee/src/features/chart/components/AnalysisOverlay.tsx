import { memo, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ExternalLink } from 'lucide-react';
import type { LiveStreamState } from '@/features/alerts/hooks/useLiveReasoningStream';

/**
 * Floating analysis overlay shown over the chart while a cycle
 * streams reasoning, when one has just finished, or when one failed.
 *
 * Theme-aware: every color comes from a CSS token, so the overlay
 * renders correctly in both dark and light modes.
 */

interface AnalysisOverlayProps {
  stream: LiveStreamState;
  onDismiss: () => void;
}

function AnalysisOverlayInner({ stream, onDismiss }: AnalysisOverlayProps) {
  const navigate = useNavigate();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [stream.reasoning]);

  const handleCheckAnalysis = () => {
    onDismiss();
    navigate(stream.analysisId ? `/analysis?id=${stream.analysisId}` : '/analysis');
  };

  const streamSymbol = stream.symbol ?? '—';

  return (
    <div
      className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-overlay animate-fade-in"
      style={{ width: 'min(800px, calc(100% - 32px))' }}
      role="dialog"
      aria-modal="true"
      aria-label="Analysis stream"
    >
      <div className="rounded-xl border border-border overflow-hidden shadow-modal bg-surface-glass">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
          <div className="flex items-center gap-2.5 min-w-0">
            {stream.isStreaming && (
              <span className="relative flex h-2 w-2 shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-brand" />
              </span>
            )}
            <span className="text-xs font-bold text-brand tracking-wide truncate">
              {streamSymbol}
            </span>
            <span className="text-[10px] font-semibold text-content-secondary uppercase truncate">
              {stream.status || 'New analysis'}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={handleCheckAnalysis}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-semibold
                         text-brand bg-brand-soft hover:bg-brand-soft-strong transition-colors duration-fast focus-ring"
              title="View in Analysis History"
            >
              <ExternalLink size={10} />
              Check
            </button>
            <button
              onClick={onDismiss}
              className="flex items-center justify-center w-6 h-6 rounded-md
                         text-content-muted hover:text-content hover:bg-surface-3 transition-colors duration-fast focus-ring"
              title="Close"
              aria-label="Close analysis overlay"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div
          ref={scrollRef}
          className="px-4 py-3 max-h-[60vh] overflow-y-auto scrollbar-thin"
        >
          {stream.error ? (
            <div className="text-xs text-warning leading-relaxed font-mono pl-3 border-l-2 border-warning whitespace-pre-wrap">
              {stream.error}
            </div>
          ) : stream.reasoning ? (
            <div className="text-xs text-content leading-relaxed font-mono pl-3 border-l-2 border-brand whitespace-pre-wrap">
              {stream.reasoning}
              {stream.isStreaming && (
                <span className="inline-block w-1.5 h-3.5 bg-brand animate-pulse ml-0.5 align-middle" />
              )}
            </div>
          ) : (
            <div className="text-xs text-content-muted font-mono pl-3 border-l-2 border-border">
              Waiting for analysis data…
              {stream.isStreaming && (
                <span className="inline-block w-1.5 h-3.5 bg-brand animate-pulse ml-1 align-middle" />
              )}
            </div>
          )}
        </div>

        {/* Live progress strip */}
        {stream.isStreaming && (
          <div className="h-0.5 bg-surface-2" aria-hidden>
            <div className="h-full bg-brand animate-pulse" style={{ width: '100%' }} />
          </div>
        )}
      </div>
    </div>
  );
}

export const AnalysisOverlay = memo(AnalysisOverlayInner);
