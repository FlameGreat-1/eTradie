import { useEffect, useRef, useState } from 'react';
import { BuilderModal } from '@/features/tradingsystem/components/BuilderModal';
import { useTradingSystemStatus } from '@/features/tradingsystem/api/hooks';
import { useSkipTradingSystem } from '@/features/tradingsystem/api/hooks';

/**
 * WelcomeBuilderModal
 *
 * Shown ONCE on the user's very first authenticated dashboard visit,
 * when their trading system status is 'none' (they have never engaged
 * with the builder or explicitly skipped it).
 *
 * PRACTICE.md (Critical Session 2) specifies:
 *   "WHEN USERS SIGNUP WE SHOW A POPUP TELLING THEM:
 *    SPARE 2-3 MINUTES TO 'BUILD YOUR EXOPER OPERATING SYSTEM'....
 *    2-3 MINUTES SINCE IT'S BIG BUT THEN CAN SKIP AND DO IT LATER"
 *
 * Suppression logic (server-side, NOT localStorage):
 *   - status === 'none'   → show the modal
 *   - status === 'active' → user already built a profile; never show
 *   - status === 'skipped'→ user explicitly skipped; never show again
 *   - status loading      → wait silently (no flash)
 *
 * Calling "Maybe later" does NOT call POST /skip. The user keeps the
 * gentle nudge in the OnboardingChecklist (step 3). Calling /skip
 * would suppress the checklist's step 3 reminder too, which is wrong.
 * The modal simply closes and will not reappear because the status
 * query is cached for 30 seconds; on the next mount the status is
 * still 'none' so the modal would show again — but only once per
 * session because we track `dismissed` in component state.
 *
 * "Start the builder" opens the existing BuilderModal (the full
 * 14-section stepper). On completion the status becomes 'active' and
 * the modal is permanently suppressed.
 */
export function WelcomeBuilderModal() {
  const { data: statusData, isLoading } = useTradingSystemStatus();
  const skipMutation = useSkipTradingSystem();

  // Track whether the user dismissed the welcome modal this session.
  // We use a ref (not state) so the dismiss does not trigger a
  // re-render that would briefly re-show the modal.
  const dismissedRef = useRef(false);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [welcomeVisible, setWelcomeVisible] = useState(false);

  useEffect(() => {
    if (isLoading) return;
    if (dismissedRef.current) return;
    // Only show when the user has never engaged with the builder.
    if (statusData?.status === 'none') {
      setWelcomeVisible(true);
    }
  }, [isLoading, statusData?.status]);

  function handleStartBuilder() {
    setWelcomeVisible(false);
    setBuilderOpen(true);
  }

  function handleMaybeLater() {
    dismissedRef.current = true;
    setWelcomeVisible(false);
  }

  // BuilderModal completion: status becomes 'active' via React Query
  // invalidation inside useSaveTradingSystem, so the next status
  // query returns 'active' and the modal is permanently suppressed.
  function handleBuilderClose() {
    setBuilderOpen(false);
  }

  if (!welcomeVisible && !builderOpen) return null;

  return (
    <>
      {welcomeVisible && (
        // Full-screen backdrop
        <div
          className="fixed inset-0 z-modal flex items-center justify-center bg-black/60 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="welcome-modal-title"
        >
          <div className="relative w-full max-w-md rounded-2xl border border-border bg-surface p-8 shadow-2xl mx-4">
            {/* Brand accent */}
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10">
                <svg
                  className="h-5 w-5 text-brand"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                  aria-hidden
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
              </div>
              <span className="text-xs font-semibold uppercase tracking-widest text-brand">
                Exoper
              </span>
            </div>

            <h2
              id="welcome-modal-title"
              className="text-xl font-bold text-content mb-2"
            >
              Build Your Exoper Operating System
            </h2>
            <p className="text-sm text-content-secondary leading-relaxed mb-6">
              Spare 2&ndash;3 minutes to configure your personal trading
              identity &mdash; your style, risk personality, session
              preferences, and execution rules. Exoper uses this to
              personalise every Exoper analysis to your exact approach.
            </p>

            <ul className="mb-6 space-y-2 text-sm text-content-secondary">
              {[
                'Tailored Exoper analysis to your trading style',
                'Risk guardrails that match your personality',
                'Execution preferences respected on every cycle',
              ].map((point) => (
                <li key={point} className="flex items-start gap-2">
                  <svg
                    className="mt-0.5 h-4 w-4 shrink-0 text-brand"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                    aria-hidden
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  {point}
                </li>
              ))}
            </ul>

            <div className="flex flex-col gap-3">
              <button
                type="button"
                onClick={handleStartBuilder}
                className="w-full rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold
                           text-white shadow-sm hover:bg-brand/90 focus-ring
                           transition-colors duration-fast"
              >
                Start the builder &rarr;
              </button>
              <button
                type="button"
                onClick={handleMaybeLater}
                className="w-full rounded-lg border border-border px-4 py-2.5 text-sm
                           font-medium text-content-secondary hover:border-content-muted
                           hover:text-content focus-ring transition-colors duration-fast"
              >
                Maybe later
              </button>
            </div>

            <p className="mt-4 text-center text-xs text-content-muted">
              You can always build it from the{' '}
              <span className="font-medium text-content">Trading System</span>{' '}
              page in the sidebar.
            </p>
          </div>
        </div>
      )}

      {/* The full 14-section builder, opened when the user clicks
          "Start the builder" from the welcome modal. */}
      <BuilderModal
        open={builderOpen}
        onClose={handleBuilderClose}
        onComplete={handleBuilderClose}
      />
    </>
  );
}
