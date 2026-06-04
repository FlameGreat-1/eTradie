import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  TradingSystemValidationError,
  defaultTradingSystem,
  useSaveTradingSystem,
  useSkipTradingSystem,
  useTradingSystem,
  type TradingSystemProfile,
} from '..';
import { useGenerateTradingPlan } from '@/features/tradingplan';
import { toast } from '@/hooks/useToast';
import { Stepper } from './Stepper';
import { Step1Identity } from './steps/Step1Identity';
import { Step2Style } from './steps/Step2Style';
import { Step3Sessions } from './steps/Step3Sessions';
import { Step4Risk } from './steps/Step4Risk';
import { Step5Confirmation } from './steps/Step5Confirmation';
import { Step6Structural } from './steps/Step6Structural';
import { Step7Entry } from './steps/Step7Entry';
import { Step8Filtering } from './steps/Step8Filtering';
import { Step9Psychology } from './steps/Step9Psychology';
import { Step10Confluence } from './steps/Step10Confluence';
import { Step11Automation } from './steps/Step11Automation';
import { Step12Assets } from './steps/Step12Assets';
import { Step13Goal } from './steps/Step13Goal';
import { Step14Management } from './steps/Step14Management';
import { ReviewStep } from './steps/ReviewStep';

const STEP_LABELS = [
  'Identity',
  'Style',
  'Sessions',
  'Risk',
  'Confirmation',
  'Structural',
  'Entry',
  'Filtering',
  'Psychology',
  'Confluence',
  'Automation',
  'Assets',
  'Goal',
  'Management',
  'Review',
] as const;
const TOTAL_STEPS = STEP_LABELS.length;

// Maps the dotted field path returned by the gateway's 422 envelope
// to the step index that contains that field. Used to jump the
// stepper back to the first step with an error so the user sees it
// immediately on submission.
const FIELD_TO_STEP: Record<string, number> = {
  'identity.': 0,
  'style': 1,
  'sessions.': 2,
  'risk.': 3,
  'confirmation': 4,
  'structural.': 5,
  'entry.': 6,
  'filtering.': 7,
  'psychology.': 8,
  'confluence.': 9,
  'automation.': 10,
  'assets.': 11,
  'goal': 12,
  'management.': 13,
};

function firstStepWithError(fields: Record<string, string>): number | null {
  for (const key of Object.keys(fields)) {
    for (const prefix of Object.keys(FIELD_TO_STEP)) {
      if (key === prefix || key.startsWith(prefix)) {
        return FIELD_TO_STEP[prefix];
      }
    }
  }
  return null;
}

interface Props {
  /** Called after a successful save. Receives the saved profile. */
  onComplete?: (profile: TradingSystemProfile) => void;
  /** Called when the user skips. */
  onSkip?: () => void;
  /**
   * When true, the page-level header (title + skip button row) is
   * suppressed because the parent (e.g. an onboarding modal) renders
   * its own chrome. Default false (standalone page mode).
   */
  embedded?: boolean;
}

export default function BuilderPage({ onComplete, onSkip, embedded = false }: Props) {
  const { data: existing, isLoading } = useTradingSystem();
  const saveMutation = useSaveTradingSystem();
  const skipMutation = useSkipTradingSystem();
  // Post-save plan trigger. Fires in the background once the trading
  // system is saved & activated so the workbook is ready (or close to
  // ready) by the time the user opens the Trading Plan view. The
  // mutation uses the platform LLM key unconditionally on the engine
  // side, so users still on the free tier get a plan without needing
  // to add their own API key first.
  const triggerPlanGeneration = useGenerateTradingPlan();

  const [profile, setProfile] = useState<TradingSystemProfile>(defaultTradingSystem);
  const [current, setCurrent] = useState(0);
  const [furthest, setFurthest] = useState(0);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [hydrated, setHydrated] = useState(false);

  // Hydrate from the user's existing profile (regenerate mode) exactly
  // once. After that the local state owns the form so React Query
  // refetches do not stomp the user's in-progress edits.
  useEffect(() => {
    if (hydrated) return;
    if (isLoading) return;
    if (existing?.profile) {
      setProfile(existing.profile);
    }
    setHydrated(true);
  }, [existing, isLoading, hydrated]);

  // Surface a load failure to the user. Without this they would
  // silently fall back to the default profile and risk overwriting an
  // existing one. Fires exactly once per error to avoid spamming the
  // toast queue on retries.


  const canSubmit = current === TOTAL_STEPS - 1 && !saveMutation.isPending;

  const handleNext = useCallback(() => {
    setCurrent((c) => {
      const next = Math.min(TOTAL_STEPS - 1, c + 1);
      setFurthest((f) => Math.max(f, next));
      return next;
    });
  }, []);

  const handleBack = useCallback(() => {
    setCurrent((c) => Math.max(0, c - 1));
  }, []);

  const handleJump = useCallback(
    (idx: number) => {
      if (idx <= furthest) setCurrent(idx);
    },
    [furthest],
  );

  const handleSave = useCallback(() => {
    saveMutation.mutate(profile, {
      onSuccess: (rec) => {
        toast({
          title: 'Trading system saved',
          description: `Version ${rec.version} is now active. Generating your 90-day plan…`,
          variant: 'success',
        });
        setErrors({});
        // Fire-and-forget plan generation. Failure is non-fatal: the
        // user can retry from the Trading Plan view at any time. We
        // do NOT await this so the builder closes immediately on a
        // successful save; the plan view subscribes to /status and
        // will reflect the generating -> active transition on its own.
        triggerPlanGeneration.mutate(undefined, {
          onError: () => {
            // Silent failure: a competing toast would distract from the
            // successful Save above. The Trading Plan view shows a
            // retry banner if the user navigates to it.
          },
        });
        onComplete?.(rec.profile ?? profile);
      },
      onError: (err) => {
        if (err instanceof TradingSystemValidationError) {
          setErrors(err.fields);
          const jumpTo = firstStepWithError(err.fields);
          if (jumpTo != null) {
            setCurrent(jumpTo);
            setFurthest((f) => Math.max(f, jumpTo));
          }
          toast({
            title: 'Please fix the highlighted fields',
            description: err.message,
            variant: 'warning',
          });
          return;
        }
        toast({
          title: 'Could not save your trading system',
          description: 'Please try again in a moment.',
          variant: 'destructive',
        });
      },
    });
  }, [profile, saveMutation, onComplete]);

  const handleSkip = useCallback(() => {
    skipMutation.mutate(undefined, {
      onSuccess: () => {
        toast({
          title: 'Skipped for now',
          description: 'You can build your trading system any time from the sidebar.',
          variant: 'default',
        });
        onSkip?.();
      },
      onError: () => {
        toast({
          title: 'Could not record skip',
          description: 'Please try again or close this dialog.',
          variant: 'warning',
        });
      },
    });
  }, [skipMutation, onSkip]);

  const stepContent = useMemo(() => {
    const common = { errors, stepNumber: current + 1, totalSteps: TOTAL_STEPS };
    switch (current) {
      case 0:
        return (
          <Step1Identity
            value={profile.identity}
            onChange={(v) => setProfile((p) => ({ ...p, identity: v }))}
            {...common}
          />
        );
      case 1:
        return (
          <Step2Style
            value={profile.style}
            onChange={(v) => setProfile((p) => ({ ...p, style: v }))}
            {...common}
          />
        );
      case 2:
        return (
          <Step3Sessions
            value={profile.sessions}
            onChange={(v) => setProfile((p) => ({ ...p, sessions: v }))}
            {...common}
          />
        );
      case 3:
        return (
          <Step4Risk
            value={profile.risk}
            onChange={(v) => setProfile((p) => ({ ...p, risk: v }))}
            {...common}
          />
        );
      case 4:
        return (
          <Step5Confirmation
            value={profile.confirmation}
            onChange={(v) => setProfile((p) => ({ ...p, confirmation: v }))}
            {...common}
          />
        );
      case 5:
        return (
          <Step6Structural
            value={profile.structural}
            onChange={(v) => setProfile((p) => ({ ...p, structural: v }))}
            {...common}
          />
        );
      case 6:
        return (
          <Step7Entry
            value={profile.entry}
            onChange={(v) => setProfile((p) => ({ ...p, entry: v }))}
            {...common}
          />
        );
      case 7:
        return (
          <Step8Filtering
            value={profile.filtering}
            onChange={(v) => setProfile((p) => ({ ...p, filtering: v }))}
            {...common}
          />
        );
      case 8:
        return (
          <Step9Psychology
            value={profile.psychology}
            onChange={(v) => setProfile((p) => ({ ...p, psychology: v }))}
            {...common}
          />
        );
      case 9:
        return (
          <Step10Confluence
            value={profile.confluence}
            onChange={(v) => setProfile((p) => ({ ...p, confluence: v }))}
            {...common}
          />
        );
      case 10:
        return (
          <Step11Automation
            value={profile.automation}
            onChange={(v) => setProfile((p) => ({ ...p, automation: v }))}
            {...common}
          />
        );
      case 11:
        return (
          <Step12Assets
            value={profile.assets}
            onChange={(v) => setProfile((p) => ({ ...p, assets: v }))}
            {...common}
          />
        );
      case 12:
        return (
          <Step13Goal
            value={profile.goal}
            onChange={(v) => setProfile((p) => ({ ...p, goal: v }))}
            {...common}
          />
        );
      case 13:
        return (
          <Step14Management
            value={profile.management}
            onChange={(v) => setProfile((p) => ({ ...p, management: v }))}
            {...common}
          />
        );
      case 14:
        return (
          <ReviewStep
            profile={profile}
            onEditStep={(idx) => setCurrent(idx)}
            stepNumber={current + 1}
            totalSteps={TOTAL_STEPS}
          />
        );
      default:
        return null;
    }
  }, [current, profile, errors]);

  if (isLoading) {
    return (
      <div className="flex flex-col h-full bg-app items-center justify-center p-6">
        <div className="relative h-24 w-24">
          <div className="absolute inset-0 rounded-full border-4 border-border border-t-brand animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <img src="/assets/sidebar/icons/logo.svg" alt="Loading" className="w-8 h-8 opacity-20" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full min-h-0 bg-white dark:bg-black transition-colors duration-300 ${!embedded ? 'pt-2 lg:px-10 pb-2 lg:pb-8' : ''}`}>
      {!embedded && (
        <div className="flex items-center justify-between gap-4 px-6 py-3 shrink-0">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-sm font-bold text-black dark:text-white uppercase tracking-wider">Trading System Builder</h1>
              <p className="text-[10px] text-black/40 dark:text-white/40 uppercase tracking-widest font-bold mt-0.5">Optimized Execution Engine</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleSkip}
            disabled={skipMutation.isPending}
            className="text-[10px] font-black text-black/30 dark:text-white/30 hover:text-black dark:hover:text-white uppercase tracking-[0.2em] transition-colors"
          >
            Skip
          </button>
        </div>
      )}

      <div className="flex-1 min-h-0 w-full lg:max-w-7xl mx-auto flex flex-col bg-black/[0.02] dark:bg-white/[0.02] rounded-3xl border border-black/10 dark:border-white/10 overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-700">
        <header className="px-6 py-2 border-b border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02] shrink-0">
          <Stepper
            current={current}
            total={TOTAL_STEPS}
            furthest={furthest}
            labels={STEP_LABELS}
            onJump={handleJump}
          />
        </header>

        <div className="flex-1 overflow-y-auto px-4 lg:px-12 py-6">
          <div className="w-full">
            {stepContent}
          </div>
        </div>

        <footer className="flex items-center justify-between gap-4 px-8 py-3 border-t border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02] shrink-0">
          <button
            type="button"
            onClick={handleBack}
            disabled={current === 0}
            className="group flex items-center gap-2 px-5 py-2.5 rounded-xl border border-black/10 dark:border-white/10 text-sm font-bold text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white hover:border-black/30 dark:hover:border-white/30 disabled:opacity-20 transition-all"
          >
            <svg className="h-4 w-4 transition-transform group-hover:-translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>
          
          <div className="flex items-center gap-3">
            {canSubmit ? (
              <button
                type="button"
                onClick={handleSave}
                disabled={saveMutation.isPending}
                className="group flex items-center gap-2 rounded-xl bg-black dark:bg-white px-8 py-2.5 text-sm font-bold text-white dark:text-black hover:opacity-90 disabled:opacity-40 transition-all shadow-lg shadow-black/10 dark:shadow-white/10"
              >
                {saveMutation.isPending ? 'Activating...' : 'Activate System'}
                <svg className="h-4 w-4 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleNext}
                disabled={current >= TOTAL_STEPS - 1}
                className="group flex items-center gap-2 rounded-xl bg-black dark:bg-white px-8 py-2.5 text-sm font-bold text-white dark:text-black hover:opacity-90 disabled:opacity-40 transition-all shadow-lg shadow-black/10 dark:shadow-white/10"
              >
                Continue
                <svg className="h-4 w-4 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            )}
          </div>
        </footer>
      </div>
    </div>
  );
}
