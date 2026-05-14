import { useState } from 'react';
import { toast } from '@/hooks/useToast';
import { LogoLoader } from '@/components/ui/LogoLoader';
import BuilderPage from '@/features/tradingsystem/components/BuilderPage';
import { ReviewStep } from '@/features/tradingsystem/components/steps/ReviewStep';
import {
  useResetTradingSystem,
  useTradingSystem,
} from '@/features/tradingsystem';
import { TradingPlanView } from '@/features/tradingplan/components/TradingPlanView';

/**
 * Standalone Trading System dashboard page.
 *
 *   status='active'  -> read-only summary with Edit + Reset actions,
 *                       PLUS a "View Trading Plan" toggle that swipes
 *                       the page over to the 90-day workbook view.
 *   status='skipped' -> friendly prompt that opens the builder.
 *   status='none'    -> identical to skipped (same empty state).
 *
 * The page is the entry point used both directly via the sidebar and
 * indirectly via the dashboard onboarding checklist's deep-link CTA.
 */

// 'system' shows the existing Trading System summary. 'plan' shows
// the 90-day Trading Plan workbook. The two are mounted side-by-side
// in a flex container; toggling translates the horizontal axis so
// the inactive view slides out while the active one slides in.
type DashboardView = 'system' | 'plan';

export default function TradingSystemPage() {
  const { data, isLoading, refetch } = useTradingSystem();
  const resetMutation = useResetTradingSystem();
  const [mode, setMode] = useState<'view' | 'edit'>('view');
  const [view, setView] = useState<DashboardView>('system');

  if (isLoading) {
    return (
      <div className="flex flex-col h-full bg-app">
        <div className="flex-1 flex items-center justify-center lg:max-w-5xl lg:mx-auto lg:w-full">
          <LogoLoader size={48} />
        </div>
      </div>
    );
  }

  const isActive = data?.status === 'active' && data.profile != null;

  if (mode === 'edit' || !isActive) {
    return (
      <BuilderPage
        onComplete={() => {
          setMode('view');
          // BuilderPage already updates the cache via setQueryData;
          // an extra refetch keeps updated_at fresh on the summary.
          void refetch();
        }}
        onSkip={() => {
          setMode('view');
          void refetch();
        }}
      />
    );
  }

  const handleReset = () => {
    if (!window.confirm(
      'Reset your Trading Operating System? This clears all your preferences and the AI will fall back to the default institutional profile. You can build a new one any time.',
    )) {
      return;
    }
    resetMutation.mutate(undefined, {
      onSuccess: () => {
        toast({
          title: 'Trading system reset',
          description: 'The AI will now use the default institutional profile until you build a new one.',
          variant: 'success',
        });
        setMode('view');
      },
      onError: () => {
        toast({
          title: 'Could not reset',
          description: 'Please try again in a moment.',
          variant: 'destructive',
        });
      },
    });
  };

  // Toggle button label flips with the active view.
  const togglingToPlan = view === 'system';
  const toggleLabel = togglingToPlan ? 'View Trading Plan' : 'View Trading System';

  return (
    <div className="flex flex-col h-full bg-app lg:max-w-5xl lg:mx-auto lg:border-x lg:border-border">
      <header className="flex items-center justify-between gap-2 px-4 py-3 border-b border-border">
        <div>
          <h1 className="text-base font-semibold text-content">
            {view === 'system' ? 'Your Trading System' : 'Your 90-Day Trading Plan'}
          </h1>
          <p className="text-xs text-content-muted">
            {view === 'system'
              ? `Version ${data!.version} · active since ${formatDate(data!.updated_at)}`
              : 'How you operate — daily journal, weekly review, discipline scorecard.'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Swipe toggle: appears whenever the trading system is active. */}
          <button
            type="button"
            onClick={() => setView(togglingToPlan ? 'plan' : 'system')}
            className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-content hover:border-content-muted focus-ring"
            aria-label={toggleLabel}
          >
            {toggleLabel}
          </button>
          {view === 'system' && (
            <>
              <button
                type="button"
                onClick={handleReset}
                disabled={resetMutation.isPending}
                className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-medium text-content-secondary
                           hover:text-content focus-ring disabled:opacity-50"
              >
                {resetMutation.isPending ? 'Resetting…' : 'Reset'}
              </button>
              <button
                type="button"
                onClick={() => setMode('edit')}
                className="rounded bg-brand px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand/90 focus-ring"
              >
                Edit
              </button>
            </>
          )}
        </div>
      </header>

      {/* Swipe viewport. Two panes stacked side-by-side; the active
          one is translated to x=0 and the inactive one is parked at
          ±100%. Transform-only animation — no layout, no reflow of
          the parent, so the transition is smooth on slow devices. */}
      <div className="flex-1 overflow-hidden">
        <div
          className="flex h-full w-[200%] transition-transform duration-300 ease-out"
          style={{ transform: view === 'system' ? 'translateX(0%)' : 'translateX(-50%)' }}
        >
          {/* Pane 1: existing Trading System summary */}
          <div className="h-full w-1/2 shrink-0 overflow-y-auto px-4 pt-4 pb-20">
            <ReviewStep
              profile={data!.profile!}
              onEditStep={() => setMode('edit')}
              stepNumber={1}
              totalSteps={1}
              hideHeader={true}
            />
          </div>
          {/* Pane 2: new Trading Plan workbook */}
          <div className="h-full w-1/2 shrink-0 overflow-y-auto px-4 pt-4 pb-20">
            <TradingPlanView />
          </div>
        </div>
      </div>
    </div>
  );
}

function formatDate(iso?: string): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}
