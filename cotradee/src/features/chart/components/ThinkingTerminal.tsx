import { memo, useEffect, useRef } from 'react';
import type { PulseEntry } from '@/features/alerts/hooks/useLiveReasoningStream';
import './ThinkingTerminal.css';

/**
 * ThinkingTerminal — Elite rolling terminal that visualises the
 * analysis pipeline in real-time.
 *
 * Each hacker-verb phase (SHARDING, DETECTING, …) occupies a single
 * row. The sub-step text after the dots updates in-place as the
 * backend hits each micro-milestone. Completed phases show a ✓ check
 * and dim slightly; active phases pulse a terminal caret.
 *
 * Visual spec:
 *   • Monospaced font, high-contrast on near-black
 *   • Brand-green (NVIDIA green #76B900) phase verbs
 *   • Auto-scroll to the latest active row
 *   • Smooth slide-up animation for new rows
 *   • Respects prefers-reduced-motion
 */

/** Dot-pad the hacker verb to a fixed visual width. */
function padPhase(phase: string): string {
  const TARGET = 14; // visual width including dots
  const dots = Math.max(3, TARGET - phase.length);
  return phase + '.'.repeat(dots);
}

interface ThinkingTerminalProps {
  pulses: PulseEntry[];
  isActive: boolean;
}

function ThinkingTerminalInner({ pulses, isActive }: ThinkingTerminalProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new pulses arrive or update.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    // Only auto-scroll if the user hasn't manually scrolled up.
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    if (isNearBottom) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    }
  }, [pulses]);

  if (pulses.length === 0 && !isActive) return null;

  return (
    <div className="thinking-terminal" aria-label="Analysis engine status">
      <div
        ref={scrollRef}
        className="thinking-terminal__scroll"
      >
        {pulses.map((entry) => (
          <div
            key={`${entry.source}-${entry.phase}-${entry.seq}`}
            className={`thinking-terminal__row ${entry.completed ? 'thinking-terminal__row--done' : 'thinking-terminal__row--active'}`}
          >
            {/* Status indicator */}
            <span className="thinking-terminal__indicator">
              {entry.completed ? (
                <svg
                  width="10"
                  height="10"
                  viewBox="0 0 10 10"
                  fill="none"
                  className="thinking-terminal__check"
                >
                  <path
                    d="M2 5.5L4 7.5L8 3"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : (
                <span className="thinking-terminal__caret" />
              )}
            </span>

            {/* Phase verb */}
            <span className="thinking-terminal__phase">
              {padPhase(entry.phase)}
            </span>

            {/* Sub-step message */}
            <span className="thinking-terminal__message">
              {entry.message}
            </span>
          </div>
        ))}

        {/* Empty active state — no pulses yet but streaming started */}
        {pulses.length === 0 && isActive && (
          <div className="thinking-terminal__row thinking-terminal__row--active">
            <span className="thinking-terminal__indicator">
              <span className="thinking-terminal__caret" />
            </span>
            <span className="thinking-terminal__phase">
              {padPhase('LOADING')}
            </span>
            <span className="thinking-terminal__message">
              Initialising analysis engine
            </span>
          </div>
        )}
      </div>

      {/* Bottom glow bar */}
      {isActive && (
        <div className="thinking-terminal__glow" aria-hidden="true" />
      )}
    </div>
  );
}

export const ThinkingTerminal = memo(ThinkingTerminalInner);
