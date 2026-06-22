import { useEffect } from 'react';
import { OnboardingChecklist } from './OnboardingChecklist';

interface Props {
  open: boolean;
  onClose: () => void;
}

/**
 * OnboardingChecklistModal
 *
 * Modal shell around the existing 7-step OnboardingChecklist so the
 * "Let's get you set up" card can be opened on demand from a welcome
 * call-to-action (or from anywhere else in the dashboard) rather than
 * being permanently mounted as the chart-empty-state.
 *
 * The checklist component itself is unchanged — every per-step CTA
 * still deep-links to its own settings page or fires the embedded
 * BuilderModal for step 3. We add no behaviour, only chrome.
 *
 * The modal mirrors BuilderModal's pattern:
 *   - capture-phase ESC handler so a parent ESC listener cannot
 *     double-fire,
 *   - body scroll lock so the page underneath does not scroll behind
 *     the open modal,
 *   - backdrop click closes; inside-click is stopped.
 */
export function OnboardingChecklistModal({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener('keydown', handler, { capture: true });
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener(
        'keydown',
        handler,
        { capture: true } as EventListenerOptions,
      );
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-modal flex items-start sm:items-center justify-center bg-black/60 px-2 py-6 sm:py-10 animate-fade-in overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-label="Let's get you set up"
      onClick={onClose}
    >
      <div
        className="relative flex flex-col w-full max-w-3xl max-h-[96vh] min-h-0 overflow-hidden rounded-xl
                   border border-border bg-app shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-3 border-b border-border px-5 py-2.5 bg-app z-10">
          <div>
            <h2 className="text-lg font-bold text-content">Let&apos;s get you set up</h2>
            <p className="text-xs text-content-muted mt-0.5">
              A few quick steps to your personalised Exoper trading desk.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-content-muted hover:text-content focus-ring"
          >
            ✕
          </button>
        </header>

        <div className="flex-1 min-h-0 overflow-y-auto">
          {/* The OnboardingChecklist component renders its own
              padded layout; we wrap it in a min-h-0 scroll area so
              long content scrolls within the modal rather than
              pushing the chrome off-screen. */}
          <OnboardingChecklist />
        </div>
      </div>
    </div>
  );
}
