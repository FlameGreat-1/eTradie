import { memo, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ExternalLink } from 'lucide-react';
import type { LiveStreamState } from '@/features/alerts/hooks/useLiveReasoningStream';
import { ThinkingTerminal } from './ThinkingTerminal';

/**
 * Floating analysis overlay shown over the chart while a cycle
 * streams reasoning, when one has just finished, or when one failed.
 *
 * Positioning rules:
 *   • Pinned to the viewport (`position: fixed`) so the overlay never
 *     drifts when the underlying main element scrolls.
 *   • On md+ screens it horizontally centres in the area to the right
 *     of the sidebar (left = sidebar width); on mobile it spans the
 *     full viewport width minus padding.
 *   • Vertically centres below the fixed header.
 *
 * Theme-aware: every colour comes from a CSS token, so the overlay
 * renders correctly in both dark and light modes.
 */

interface AnalysisOverlayProps {
  stream: LiveStreamState;
  onDismiss: () => void;
}

function AnalysisOverlayInner({ stream, onDismiss }: AnalysisOverlayProps) {
  const navigate = useNavigate();
  const scrollRef = useRef<HTMLDivElement>(null);

  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef({ startX: 0, startY: 0, initX: 0, initY: 0 });

  useEffect(() => {
    if (!isDragging) return;

    const onMove = (e: MouseEvent) => {
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      setPos({
        x: dragRef.current.initX + dx,
        y: dragRef.current.initY + dy,
      });
    };

    const onUp = () => setIsDragging(false);

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [isDragging]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [stream.reasoning]);

  // Close on Escape, like a proper dialog.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDismiss();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onDismiss]);

  const handleCheckAnalysis = () => {
    onDismiss();
    navigate(stream.analysisId ? `/dashboard/analysis?id=${stream.analysisId}` : '/dashboard/analysis');
  };

  const streamSymbol = stream.symbol ?? '—';

  // The ThinkingTerminal is visible when we have pulse events OR
  // when the stream is active but reasoning hasn't started yet.
  const showTerminal = stream.pulses.length > 0 || (stream.isStreaming && !stream.reasoning);

  return (
    <div
      className="fixed z-overlay animate-fade-in pointer-events-none"
      style={{
        top: 'var(--header-height)',
        bottom: 0,
        left: 'var(--main-left, 0px)',
        right: 0,
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Analysis stream"
    >
      <div
        className="absolute top-1/2 left-1/2 pointer-events-auto"
        style={{ 
          width: 'min(800px, calc(100% - 32px))',
          transform: `translate(calc(-50% + ${pos.x}px), calc(-50% + ${pos.y}px))`
        }}
      >
        <div className="rounded-2xl border border-border overflow-hidden shadow-2xl">
          {/* Header */}
          <div 
            className={`flex items-center justify-between px-5 py-4 border-b border-border bg-surface-1/50 ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
            onMouseDown={(e) => {
              if ((e.target as HTMLElement).closest('button')) return;
              setIsDragging(true);
              dragRef.current = {
                startX: e.clientX,
                startY: e.clientY,
                initX: pos.x,
                initY: pos.y,
              };
            }}
          >
            <div className="flex items-center gap-3 min-w-0">
              {stream.isStreaming && (
                <span className="relative flex h-2 w-2 shrink-0">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-brand" />
                </span>
              )}
              <div className="flex items-center gap-2 truncate">
                <span className="text-[13px] font-black text-brand tracking-wide uppercase">
                  {streamSymbol}
                </span>
                <span className="w-1 h-1 rounded-full bg-border" />
                <span className="text-[11px] font-bold text-content-muted uppercase tracking-wider">
                  {stream.status || 'New analysis'}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCheckAnalysis}
                className="flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-[10px] font-black
                           text-brand bg-brand/10 hover:bg-brand/20 transition-all duration-fast focus-ring uppercase tracking-wider"
                title="View in Analysis History"
              >
                <ExternalLink size={12} />
                Check
              </button>
              <button
                onClick={onDismiss}
                className="flex items-center justify-center w-8 h-8 rounded-xl
                           text-content-muted hover:text-content hover:bg-surface-3 transition-all duration-fast focus-ring"
                title="Close"
                aria-label="Close analysis overlay"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Thinking Terminal — real-time analysis pipeline visualiser */}
          {showTerminal && (
            <ThinkingTerminal
              pulses={stream.pulses}
              isActive={stream.isStreaming}
            />
          )}

          {/* Body — reasoning text / error / waiting */}
          <div
            ref={scrollRef}
            className="px-6 py-5 max-h-[60vh] overflow-y-auto no-scrollbar"
          >
            {stream.error ? (
              <div className="text-[12px] text-danger leading-relaxed font-mono pl-4 border-l-2 border-danger whitespace-pre-wrap">
                {stream.error}
              </div>
            ) : stream.reasoning ? (
              <div className="text-[12px] text-content-secondary leading-relaxed font-mono pl-4 border-l-2 border-brand/50 whitespace-pre-wrap">
                {stream.reasoning}
                {stream.isStreaming && (
                  <span className="inline-block w-1.5 h-4 bg-brand animate-pulse ml-1 align-middle" />
                )}
              </div>
            ) : !showTerminal ? (
              <div className="text-[12px] text-content-muted font-mono pl-4 border-l-2 border-border">
                Waiting for analysis data…
                {stream.isStreaming && (
                  <span className="inline-block w-1.5 h-4 bg-brand animate-pulse ml-1 align-middle" />
                )}
              </div>
            ) : null}
          </div>

          {/* Live progress strip */}
          {stream.isStreaming && (
            <div className="h-0.5 bg-surface-2" aria-hidden>
              <div className="h-full bg-brand animate-pulse" style={{ width: '100%' }} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export const AnalysisOverlay = memo(AnalysisOverlayInner);

