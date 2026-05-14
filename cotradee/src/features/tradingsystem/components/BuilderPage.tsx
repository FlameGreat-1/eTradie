import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  TradingSystemValidationError,
  defaultTradingSystem,
  useSaveTradingSystem,
  useSkipTradingSystem,
  useTradingSystem,
  type TradingSystemProfile,
} from '..';
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
          description: `Version ${rec.version} is now active.`,
          variant: 'success',
        });
        setErrors({});
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
      <div className="flex items-center justify-center h-64 text-sm text-content-muted">
        Loading your trading system…
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-app">
      {!embedded && (
        <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-border">
          <div>
            <h1 className="text-base font-semibold text-content">Build Your Exoper Trading System</h1>
            <p className="text-xs text-content-muted">Takes 2–3 minutes. You can change every answer later.</p>
          </div>
          <button
            type="button"
            onClick={handleSkip}
            disabled={skipMutation.isPending}
            className="text-xs font-medium text-content-secondary hover:text-content focus-ring rounded px-2 py-1"
          >
            Skip for now
          </button>
        </div>
      )}

      <Stepper
        current={current}
        total={TOTAL_STEPS}
        furthest={furthest}
        labels={STEP_LABELS}
        onJump={handleJump}
      />

      <div className="flex-1 overflow-y-auto px-4 py-4">{stepContent}</div>

      <div className="flex items-center justify-between gap-2 border-t border-border bg-surface px-4 py-3">
        <button
          type="button"
          onClick={handleBack}
          disabled={current === 0}
          className="rounded border border-border bg-surface px-3 py-1.5 text-sm font-medium text-content-secondary
                     hover:text-content disabled:opacity-40 disabled:cursor-not-allowed focus-ring"
        >
          Back
        </button>
        {canSubmit ? (
          <button
            type="button"
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="rounded bg-brand px-4 py-1.5 text-sm font-semibold text-white hover:bg-brand/90
                       disabled:opacity-60 disabled:cursor-not-allowed focus-ring"
          >
            {saveMutation.isPending ? 'Saving…' : 'Save & Activate'}
          </button>
        ) : (
          <button
            type="button"
            onClick={handleNext}
            disabled={current >= TOTAL_STEPS - 1}
            className="rounded bg-brand px-4 py-1.5 text-sm font-semibold text-white hover:bg-brand/90
                       disabled:opacity-60 disabled:cursor-not-allowed focus-ring"
          >
            Next
          </button>
        )}
      </div>
    </div>
  );
}
