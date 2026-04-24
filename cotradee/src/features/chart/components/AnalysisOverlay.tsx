import { memo, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ExternalLink } from 'lucide-react';
import type { LiveStreamState } from '@/features/alerts/hooks/useLiveReasoningStream';

/**
 * Floating analysis overlay that appears on top of the chart
 * when an analysis is streaming, has just completed, or failed.
 *
 * Lifetime rules (matches the user-facing contract):
 *   - The overlay stays visible after `final` until the user dismisses
 *     it (X) or a new cycle for a different symbol replaces it.
 *   - The reasoning text inside NEVER auto-disappears on a timer; it
 *     is cleared only when the hook's `reset()` is called (on X) or
 *     when the underlying reducer receives a `status` frame for a
 *     different symbol.
 *
 * Features:
 *   - Glassmorphism styling with subtle backdrop blur
 *   - Live token streaming with cursor animation
 *   - "X" to dismiss and "Check" to open in Analysis History
 *   - Auto-scrolls to the bottom as new tokens arrive
 */

interface AnalysisOverlayProps {
  stream: LiveStreamState;
  /** Called when the user clicks the X button to dismiss. */
  onDismiss: () => void;
}

function AnalysisOverlayInner({ stream, onDismiss }: AnalysisOverlayProps) {
  const navigate = useNavigate();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom as new reasoning tokens arrive.
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [stream.reasoning]);

  const handleCheckAnalysis = () => {
    onDismiss();
    if (stream.analysisId) {
      navigate(`/analysis?id=${stream.analysisId}`);
    } else {
      navigate('/analysis');
    }
  };

  const streamSymbol = stream.symbol ?? '—';

  return (
    <div
      className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 animate-fade-in"
      style={{ width: 'min(800px, calc(100% - 32px))' }}
    >
      <div
        className="rounded-xl border border-border overflow-hidden shadow-2xl"
        style={{
          background: 'rgba(10, 10, 15, 0.85)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50">
          <div className="flex items-center gap-2.5">
            {stream.isStreaming && (
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-brand" />
              </span>
            )}
            <span className="text-xs font-bold text-brand tracking-wide">
              {streamSymbol}
            </span>
            <span className="text-[10px] font-semibold text-content-secondary uppercase">
              {stream.status || 'New Analysis'}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            {/* Check button — navigate to analysis history */}
            <button
              onClick={handleCheckAnalysis}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-semibold
                         text-white bg-brand/10 hover:bg-brand/20 transition-colors"
              title="View in Analysis History"
            >
              <ExternalLink size={10} />
              Check
            </button>
            {/* Dismiss button */}
            <button
              onClick={onDismiss}
              className="flex items-center justify-center w-6 h-6 rounded-md
                         text-content-muted hover:text-content hover:bg-surface-2/50 transition-colors"
              title="Close"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Streaming / held body */}
        <div
          ref={scrollRef}
          className="px-4 py-3 max-h-[60vh] overflow-y-auto scrollbar-thin"
        >
          {stream.error ? (
            <div className="text-xs text-warning leading-relaxed font-mono pl-3 border-l-2 border-warning/50 whitespace-pre-wrap">
              {stream.error}
            </div>
          ) : stream.reasoning ? (
            <div className="text-xs text-white/90 leading-relaxed font-mono pl-3 border-l-2 border-brand/40 whitespace-pre-wrap">
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

        {/* Live progress bar (only while actively streaming) */}
        {stream.isStreaming && (
          <div className="h-0.5 bg-surface-2">
            <div className="h-full bg-brand animate-pulse" style={{ width: '100%' }} />
          </div>
        )}
      </div>
    </div>
  );
}

export const AnalysisOverlay = memo(AnalysisOverlayInner);
