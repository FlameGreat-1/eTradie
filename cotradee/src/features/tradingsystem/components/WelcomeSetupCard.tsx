import { useState } from 'react';
import { OnboardingChecklistModal } from './OnboardingChecklistModal';

/**
 * WelcomeSetupCard
 *
 * Empty-state hero shown on the dashboard immediately after
 * registration + login while the user has not yet connected a
 * broker. Replaces the previous behaviour where the 7-step checklist
 * was rendered directly inline as the chart-empty-state.
 *
 * Click "Get started" → opens OnboardingChecklistModal which
 * surfaces the full 7-step "Let's get you set up" flow on top of
 * the dashboard background.
 *
 * This card is intentionally separate from WelcomeBuilderModal
 * (which is about the 14-section Trading System builder and is
 * mounted globally in DashboardLayout). The two coexist:
 *
 *   - WelcomeBuilderModal:  "Build Your Exoper Operating System"
 *                           → 14-section trading-system builder.
 *                           Triggered by status='none'; can be
 *                           dismissed and revisited any time.
 *
 *   - WelcomeSetupCard:     "Welcome to Exoper. Connect your broker…"
 *                           → 7-step Let's-get-you-set-up checklist.
 *                           Renders on the dashboard whenever the
 *                           user cannot see a chart because they
 *                           have not connected a broker yet.
 */
export function WelcomeSetupCard() {
  const [checklistOpen, setChecklistOpen] = useState(false);

  return (
    <>
      <div className="flex h-full w-full items-center justify-center px-4 py-8">
        <div className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 sm:p-8 shadow-sm text-center">
          {/* Brand accent */}
          <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-brand/10">
            <svg
              className="h-6 w-6 text-brand"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          </div>

          <h2 className="text-xl font-bold text-content">Welcome to Exoper</h2>
          <p className="mt-2 text-sm text-content-secondary leading-relaxed">
            Setup and configure your account to start experiencing Exoper. It only
            takes a few minutes, and you can revisit any step later from settings.
          </p>

          <ul className="mx-auto mt-5 max-w-sm space-y-2 text-left text-sm text-content-secondary">
            {[
              'Connect your MT4 or MT5 broker',
              'Pick the symbols you want analysed',
              'Build your personal trading system',
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
                <span>{point}</span>
              </li>
            ))}
          </ul>

          <button
            type="button"
            onClick={() => setChecklistOpen(true)}
            className="mt-6 w-full rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white shadow-sm
                       hover:bg-brand/90 focus-ring transition-colors duration-fast"
          >
            Get started
          </button>

          <p className="mt-3 text-xs text-content-muted">
            You can also reach this from{' '}
            <span className="font-medium text-content">Settings → Broker</span>{' '}
            any time.
          </p>
        </div>
      </div>

      <OnboardingChecklistModal
        open={checklistOpen}
        onClose={() => setChecklistOpen(false)}
      />
    </>
  );
}
