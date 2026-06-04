import { useState, useEffect } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from '@/hooks/useToast';
import { LogoLoader } from '@/components/ui/LogoLoader';
import BuilderPage from '@/features/tradingsystem/components/BuilderPage';

import {
  useResetTradingSystem,
  useTradingSystem,
  type TradingSystemProfile,
} from '@/features/tradingsystem';
import { TradingPlanView } from '@/features/tradingplan/components/TradingPlanView';

/* ── Tab definitions for the system read-only view ────────────── */
const SYSTEM_TABS = [
  { id: 'identity',     label: 'Identity' },
  { id: 'style',        label: 'Style' },
  { id: 'sessions',     label: 'Sessions' },
  { id: 'risk',         label: 'Risk' },
  { id: 'confirmation', label: 'Confirm' },
  { id: 'structural',   label: 'Structural' },
  { id: 'entry',        label: 'Entry' },
  { id: 'filtering',    label: 'Filtering' },
  { id: 'psychology',   label: 'Psychology' },
  { id: 'confluence',   label: 'Confluence' },
  { id: 'automation',   label: 'Automation' },
  { id: 'assets',       label: 'Assets' },
  { id: 'goal',         label: 'Goal' },
  { id: 'management',   label: 'Management' },
] as const;

type SystemTabId = (typeof SYSTEM_TABS)[number]['id'];

/* ── Helpers ──────────────────────────────────────────────────── */
function yesNo(b: boolean) { return b ? 'Yes' : 'No'; }
function joinList(items: string[]) { return !items?.length ? '—' : items.join(', '); }

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 py-3 border-b border-black/[0.03] dark:border-white/[0.03] last:border-b-0">
      <span className="text-[10px] uppercase font-bold tracking-wider text-black/30 dark:text-white/30">{label}</span>
      <span className="text-xs font-bold text-black dark:text-white text-right">{value}</span>
    </div>
  );
}

function SystemTabContent({ tabId, profile }: { tabId: SystemTabId; profile: TradingSystemProfile }) {
  const { identity, sessions, risk, structural, entry, filtering, psychology, confluence, automation, assets, management } = profile;

  switch (tabId) {
    case 'identity':
      return (
        <>
          <Row label="Experience" value={identity.experience} />
          <Row label="Execution" value={identity.automation} />
          <Row label="Risk appetite" value={identity.risk_appetite} />
          <Row label="Trader type" value={identity.trader_type} />
          <Row label="Discipline" value={identity.discipline} />
        </>
      );
    case 'style':
      return <Row label="Style" value={profile.style} />;
    case 'sessions':
      return (
        <>
          <Row label="Preferred" value={joinList(sessions.preferred_sessions)} />
          <Row label="Avoid low liquidity" value={yesNo(sessions.avoid_low_liquidity)} />
          <Row label="High-volatility windows only" value={yesNo(sessions.high_volatility_windows_only)} />
        </>
      );
    case 'risk':
      return (
        <>
          <Row label="Risk model" value={risk.risk_model} />
          <Row label="Per-trade risk" value={`${risk.fixed_risk_percent}%`} />
          <Row label="Max daily drawdown" value={`${risk.max_daily_drawdown_percent}%`} />
          <Row label="Max weekly drawdown" value={`${risk.max_weekly_drawdown_percent}%`} />
          <Row label="Max simultaneous" value={String(risk.max_simultaneous_trades)} />
          <Row label="Max correlated" value={String(risk.max_correlated_exposure)} />
          <Row label="Partial TPs" value={yesNo(risk.partial_take_profits)} />
          <Row label="Break-even mgmt" value={yesNo(risk.break_even_management)} />
          <Row label="Trailing stop" value={yesNo(risk.trailing_stop_enabled)} />
        </>
      );
    case 'confirmation':
      return <Row label="Strictness" value={profile.confirmation} />;
    case 'structural':
      return (
        <>
          <Row label="Frameworks" value={joinList(structural.frameworks)} />
          <Row label="FVG" value={yesNo(structural.use_fvg)} />
          <Row label="Order Blocks" value={yesNo(structural.use_order_blocks)} />
          <Row label="CHoCH / BMS" value={yesNo(structural.use_choch_bms)} />
          <Row label="IDM" value={yesNo(structural.use_idm)} />
          <Row label="Emphasis" value={structural.structure_emphasis} />
        </>
      );
    case 'entry':
      return (
        <>
          <Row label="Execution mode" value={entry.execution_mode} />
          <Row label="Confirmation candle" value={yesNo(entry.require_confirmation_candle)} />
          <Row label="Retest" value={yesNo(entry.require_retest)} />
          <Row label="Liquidity sweep" value={yesNo(entry.require_liquidity_sweep)} />
          <Row label="MTF alignment" value={yesNo(entry.require_mtf_alignment)} />
        </>
      );
    case 'filtering':
      return (
        <>
          <Row label="Minimum RR" value={`${filtering.minimum_rr}:1`} />
          <Row label="Avoid counter-trend" value={yesNo(filtering.avoid_counter_trend)} />
          <Row label="Avoid news" value={yesNo(filtering.avoid_news_volatility)} />
          <Row label="Avoid ranging" value={yesNo(filtering.avoid_ranging_markets)} />
          <Row label="Avoid overnight" value={yesNo(filtering.avoid_overnight_holds)} />
          <Row label="Avoid Friday" value={yesNo(filtering.avoid_friday_trades)} />
          <Row label="Avoid session transitions" value={yesNo(filtering.avoid_session_transitions)} />
        </>
      );
    case 'psychology':
      return (
        <>
          <Row label="Max losses" value={String(psychology.max_losses_before_cooldown)} />
          <Row label="Loss-streak cooldown" value={yesNo(psychology.cooldown_after_loss_streak)} />
          <Row label="Daily lockout" value={yesNo(psychology.daily_lockout_after_target)} />
          <Row label="Revenge protection" value={yesNo(psychology.revenge_trading_protection)} />
          <Row label="Overtrading protection" value={yesNo(psychology.overtrading_protection)} />
          <Row label="Volatility sensitivity" value={psychology.emotional_volatility_sensitivity} />
        </>
      );
    case 'confluence':
      return (
        <>
          <Row label="Macro" value={String(confluence.macro_alignment)} />
          <Row label="DXY" value={String(confluence.dxy)} />
          <Row label="COT" value={String(confluence.cot)} />
          <Row label="HTF" value={String(confluence.htf_alignment)} />
          <Row label="Wyckoff" value={String(confluence.wyckoff)} />
          <Row label="Volume / liquidity" value={String(confluence.volume_liquidity)} />
          <Row label="Session timing" value={String(confluence.session_timing)} />
        </>
      );
    case 'automation':
      return (
        <>
          <Row label="Mode" value={automation.mode} />
          <Row label="Final confirmation" value={yesNo(automation.require_final_confirmation)} />
          <Row label="Unattended execution" value={yesNo(automation.allow_unattended_execution)} />
        </>
      );
    case 'assets':
      return (
        <>
          <Row label="Classes" value={joinList(assets.asset_classes)} />
          <Row label="Preferred pairs" value={joinList(assets.preferred_pairs)} />
          <Row label="Avoid high volatility" value={yesNo(assets.avoid_highly_volatile)} />
          <Row label="Avoid correlated" value={yesNo(assets.avoid_correlated_instruments)} />
        </>
      );
    case 'goal':
      return <Row label="Orientation" value={profile.goal} />;
    case 'management':
      return (
        <>
          <Row label="Partial TP style" value={management.partial_tp_style} />
          <Row label="Trailing stop" value={management.trailing_stop} />
          <Row label="Break-even trigger" value={management.break_even_trigger} />
          <Row label="Scale-in" value={yesNo(management.scale_in_enabled)} />
          <Row label="Scale-out" value={yesNo(management.scale_out_enabled)} />
          <Row label="Hold runners" value={yesNo(management.hold_runners)} />
          <Row label="Close before news" value={yesNo(management.close_before_news)} />
        </>
      );
  }
}


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
  const [activeSystemTab, setActiveSystemTab] = useState<SystemTabId>('identity');
  
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

  // ScrollSpy to update active tab based on what section is currently in view
  useEffect(() => {
    if (mode !== 'view' || view !== 'system') return;
    
    // We observe all the section elements. When they cross the top 20%-30% of the screen, we consider them "active".
    const observer = new IntersectionObserver((entries) => {
      // Find the first intersecting entry that is mostly visible
      for (const entry of entries) {
        if (entry.isIntersecting) {
          const tabId = entry.target.id.replace('system-section-', '') as SystemTabId;
          setActiveSystemTab(tabId);
        }
      }
    }, {
      rootMargin: '-20% 0px -70% 0px', // Trigger when section is near the top
      threshold: 0
    });

    SYSTEM_TABS.forEach(tab => {
      const el = document.getElementById(`system-section-${tab.id}`);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [mode, view, data?.profile]);

  // Keep the active tab button visible in the scrollable tab bar
  useEffect(() => {
    if (mode !== 'view' || view !== 'system') return;
    
    const btn = document.getElementById(`tab-btn-${activeSystemTab}`);
    const container = document.getElementById('system-tab-container');
    
    if (btn && container) {
      const containerRect = container.getBoundingClientRect();
      const btnRect = btn.getBoundingClientRect();
      
      // If button is outside the horizontal viewport of the container, scroll to center it
      if (btnRect.left < containerRect.left || btnRect.right > containerRect.right) {
        const scrollLeft = btn.offsetLeft - container.offsetWidth / 2 + btn.offsetWidth / 2;
        container.scrollTo({ left: scrollLeft, behavior: 'smooth' });
      }
    }
  }, [activeSystemTab, mode, view]);

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
      <div className={`flex flex-col h-full bg-app transition-all duration-300 w-full`}>
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
    <div className={`flex flex-col h-full bg-app transition-all duration-300 ${
      view === 'system'
        ? 'lg:max-w-7xl lg:mx-auto'
        : 'w-full'
    }`}>
      <header className="flex items-center justify-between gap-2 px-4 py-3 border-b border-border shrink-0">
        <div>
          <h1 className="text-base font-semibold text-content">
            {view === 'system' ? (
              <><span className="hidden sm:inline">Your </span>Trading System</>
            ) : (
              <><span className="hidden sm:inline">Your </span>90-Day Trading Plan</>
            )}
          </h1>
          {view === 'plan' && (
            <p className="text-xs text-content-muted">
              How you operate — daily journal, weekly review, discipline scorecard.
            </p>
          )}
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
          {/* Pane 1: existing Trading System summary — tabbed */}
          <div className="relative h-full w-1/2 shrink-0 overflow-y-auto px-2 sm:px-4 pt-4 pb-20 custom-scrollbar">
            {/* Tab bar (Sticky) */}
            <div className="sticky top-0 z-20 bg-app pb-4 pt-2 -mt-2">
              <div id="system-tab-container" className="flex overflow-x-auto items-center justify-start gap-1 bg-black/5 dark:bg-white/5 p-1 rounded-xl border border-black/5 dark:border-white/5 w-full no-scrollbar">
                {SYSTEM_TABS.map((tab) => {
                  const active = activeSystemTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      id={`tab-btn-${tab.id}`}
                      type="button"
                      onClick={() => {
                        const el = document.getElementById(`system-section-${tab.id}`);
                        if (el) {
                          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                        setActiveSystemTab(tab.id);
                      }}
                      className={`rounded-lg px-3 py-1.5 text-[10px] font-black uppercase tracking-wider transition-all duration-200 whitespace-nowrap shrink-0 ${
                        active
                          ? 'bg-black dark:bg-white text-white dark:text-black shadow-sm'
                          : 'text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white hover:bg-black/[0.02] dark:hover:bg-white/[0.02]'
                      }`}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Content: All sections stacked in a single card */}
            <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-5 shadow-sm">
              {SYSTEM_TABS.map((tab, idx) => (
                <div key={tab.id} id={`system-section-${tab.id}`} className="scroll-mt-[120px] pb-8 last:pb-0">
                  {/* Header: Circle Step Indicator + Title */}
                  <div className="flex items-center gap-3 mb-5">
                    <div className="w-9 h-9 rounded-full border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 flex items-center justify-center shrink-0">
                      <span className="text-[10px] font-black text-black/60 dark:text-white/60">{idx + 1}/{SYSTEM_TABS.length}</span>
                    </div>
                    <h3 className="text-xs font-black text-brand uppercase tracking-[0.2em] m-0">
                      {tab.label}
                    </h3>
                  </div>
                  
                  {/* Rows */}
                  <div className="pl-12 space-y-1">
                    <SystemTabContent tabId={tab.id} profile={data!.profile!} />
                  </div>

                  {/* Divider except on the very last item */}
                  {idx < SYSTEM_TABS.length - 1 && (
                    <div className="h-px bg-black/5 dark:border-white/5 mt-8 ml-12" />
                  )}
                </div>
              ))}
            </div>
          </div>
          {/* Pane 2: new Trading Plan workbook */}
          <div className="h-full w-1/2 shrink-0 overflow-y-auto px-2 sm:px-4 pt-4 pb-20">
            <TradingPlanView />
          </div>
        </div>
      </div>
    </div>
  );
}

