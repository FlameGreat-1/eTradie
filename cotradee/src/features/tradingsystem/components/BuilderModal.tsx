import { useEffect } from 'react';
import BuilderPage from './BuilderPage';
import type { TradingSystemProfile } from '../types';

interface Props {
  open: boolean;
  onClose: () => void;
  onComplete?: (profile: TradingSystemProfile) => void;
  onSkip?: () => void;
}

/**
 * Modal wrapper around BuilderPage. Used by the dashboard onboarding
 * checklist's step 3 so the user can build their trading system
 * without leaving the dashboard.
 *
 * BuilderPage is rendered with embedded=true so it suppresses its
 * own page-level header; the modal renders its own chrome (title,
 * close button, ESC handler) instead.
 */
export function BuilderModal({ open, onClose, onComplete, onSkip }: Props) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // Consume the keystroke so any parent-level ESC listener
        // (e.g. a sidebar drawer or a confirmation dialog above this
        // modal) does not fire alongside ours.
        e.stopPropagation();
        e.preventDefault();
        onClose();
      }
    };
    // capture: true so we run BEFORE any document-level listener
    // installed by a parent (React's synthetic event system bubbles
    // through a single root listener; native capture-phase fires
    // before it).
    document.addEventListener('keydown', handler, { capture: true });
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handler, { capture: true } as EventListenerOptions);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center bg-black/55 px-4 py-6 animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-label="Build Your Trading System"
      onClick={onClose}
    >
      <div
        className="relative flex flex-col w-full max-w-2xl max-h-[92vh] overflow-hidden rounded-xl
                   border border-border bg-surface shadow-pop"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <h2 className="text-base font-semibold text-content">Build Your Exoper Trading System</h2>
            <p className="text-xs text-content-muted">
              2–3 minutes. Every answer can be changed later from the Trading System page.
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
        <div className="flex-1 overflow-hidden">
          <BuilderPage
            embedded
            onComplete={(profile) => {
              onComplete?.(profile);
              onClose();
            }}
            onSkip={() => {
              onSkip?.();
              onClose();
            }}
          />
        </div>
      </div>
    </div>
  );
}
