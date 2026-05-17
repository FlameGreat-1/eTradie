import { useState, useEffect } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
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
  
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const justActivated = searchParams.get('just_activated') === 'true';
  const view: DashboardView = location.pathname.endsWith('/trading-plan') ? 'plan' : 'system';

  // Clear the just_activated param if the user switches to the plan view manually
  useEffect(() => {
    if (view === 'plan' && justActivated) {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('just_activated');
      setSearchParams(nextParams, { replace: true });
    }
  }, [view, justActivated, searchParams, setSearchParams]);

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

  if (!isActive && view === 'plan') {
    return (
      <div className="flex flex-col h-full bg-app lg:max-w-5xl lg:mx-auto lg:border-x lg:border-border">
        <header className="flex items-center justify-between gap-2 px-4 py-3 border-b border-border shrink-0">
          <div>
            <h1 className="text-base font-semibold text-content">
              <span className="hidden sm:inline">Your </span>90-Day Trading Plan
            </h1>
            <p className="text-xs text-content-muted">
              How you operate — daily journal, weekly review, discipline scorecard.
            </p>
          </div>
        </header>
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center animate-in fade-in zoom-in-95 duration-500">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-black/5 dark:bg-white/5 text-black/40 dark:text-white/40 mb-6 shadow-xl">
            <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-content mb-2 tracking-tight">System Required</h2>
          <p className="text-sm text-content-muted max-w-md mx-auto mb-8 leading-relaxed">
            Your personalized 90-Day Trading Plan requires a defined Trading System to generate. Build your system first, and our AI will automatically construct your plan.
          </p>
          <button
            onClick={() => navigate('/dashboard/trading-system')}
            className="rounded-xl bg-black dark:bg-white px-8 py-3 text-[10px] font-black text-white dark:text-black uppercase tracking-widest hover:opacity-90 transition-all shadow-lg shadow-black/10 dark:shadow-white/10"
          >
            Build Trading System &rarr;
          </button>
        </div>
      </div>
    );
  }

  if (mode === 'edit' || !isActive) {
    return (
      <BuilderPage
        onComplete={() => {
          setMode('view');
          void refetch();
          navigate('/dashboard/trading-system?just_activated=true');
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

  const togglingToPlan = view === 'system';
  const toggleLabel = togglingToPlan ? 'View Trading Plan' : 'View Trading System';

  return (
    <div className="flex flex-col h-full bg-app lg:max-w-5xl lg:mx-auto lg:border-x lg:border-border">
      <header className="flex items-center justify-between gap-2 px-4 py-3 border-b border-border shrink-0">
        <div>
          <h1 className="text-base font-semibold text-content">
            {view === 'system' ? (
              <><span className="hidden sm:inline">Your </span>Trading System</>
            ) : (
              <><span className="hidden sm:inline">Your </span>90-Day Trading Plan</>
            )}
          </h1>
          <p className="text-xs text-content-muted">
            {view === 'system'
              ? `Version ${data!.version} · active since ${formatDate(data!.updated_at)}`
              : 'How you operate — daily journal, weekly review, discipline scorecard.'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => navigate(togglingToPlan ? '/dashboard/trading-plan' : '/dashboard/trading-system')}
            className={`rounded border px-3 py-1.5 text-xs font-semibold focus-ring transition-all duration-500 ${
              justActivated && togglingToPlan
                ? 'border-brand bg-brand/10 text-brand shadow-[0_0_15px_rgba(var(--brand-rgb),0.4)] animate-pulse'
                : 'border-border bg-surface text-content hover:border-content-muted'
            }`}
            aria-label={toggleLabel}
          >
            <span className="hidden sm:inline">{togglingToPlan ? 'View ' : 'View '}</span>
            {togglingToPlan ? 'Trading Plan' : 'Trading System'}
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

      {justActivated && view === 'system' && (
        <div className="bg-brand/10 border-b border-brand/20 px-4 py-3 flex items-center justify-between shrink-0 animate-in slide-in-from-top-2 fade-in duration-500">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand/20 text-brand">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-bold text-brand">Trading System Activated!</p>
              <p className="text-[11px] text-content-muted mt-0.5">We are now using it to generate your personalized 90-Day Trading Plan.</p>
            </div>
          </div>
          <button
            onClick={() => navigate('/dashboard/trading-plan')}
            className="text-[10px] font-black text-brand hover:text-brand/80 transition-colors uppercase tracking-widest shrink-0 ml-4"
          >
            View Generation &rarr;
          </button>
        </div>
      )}

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
              hideSectionEdits={true}
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
