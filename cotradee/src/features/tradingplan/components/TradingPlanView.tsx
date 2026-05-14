import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from '@/hooks/useToast';
import { LogoLoader } from '@/components/ui/LogoLoader';
import {
  downloadPlanAsExcel,
  tradingPlanKeys,
  useGenerateTradingPlan,
  useResetTradingPlan,
  useTradingPlan,
  useTradingPlanStatus,
  useUpdateTradingPlan,
  type TradingPlan,
} from '..';
import { TraderProfileSection } from './sections/TraderProfileSection';
import { AccountParametersSection } from './sections/AccountParametersSection';
import { JournalSection } from './sections/JournalSection';
import { WeeklyReviewSection } from './sections/WeeklyReviewSection';
import { ScorecardSection } from './sections/ScorecardSection';
import { ObjectivesSection } from './sections/ObjectivesSection';
import { FooterMetadata } from './sections/FooterMetadata';
import { GenerateBanner } from './GenerateBanner';

/**
 * Top-level Trading Plan view. Rendered inside the swipe-toggle on
 * the Trading System dashboard page.
 *
 * Rendering modes:
 *   - status='active'     — read-only render of the workbook with
 *                           Edit, Regenerate, Export, Reset actions.
 *   - status='generating' — spinner card via GenerateBanner, plus
 *                           the existing plan underneath (if any) so
 *                           the user does not lose context.
 *   - status='failed'     — retry banner + the existing plan (if any).
 *   - status='none'       — Generate CTA.
 *
 * Edit flow: clicking Edit clones the plan into a local draft. All
 * sub-sections receive the draft + onChange callbacks. Saving PUTs
 * the draft via useUpdateTradingPlan (no LLM call, version unchanged).
 */
export function TradingPlanView() {
  const qc = useQueryClient();
  const { data: planRec, isLoading } = useTradingPlan();
  const { data: statusView } = useTradingPlanStatus();
  const generate = useGenerateTradingPlan();
  const update = useUpdateTradingPlan();
  const reset = useResetTradingPlan();

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<TradingPlan | null>(null);

  // When the polling status transitions OUT of 'generating' (either
  // to 'active' or 'failed'), invalidate the full-plan query so the
  // SPA fetches the freshly-persisted workbook without waiting for
  // the 30-second staleTime to elapse. Tracked via a ref so the
  // invalidation fires once per transition, not on every render.
  const lastStatusRef = useRef<typeof statusView extends undefined ? undefined : string | undefined>(undefined);
  useEffect(() => {
    const current = statusView?.status;
    const previous = lastStatusRef.current;
    if (previous === 'generating' && (current === 'active' || current === 'failed')) {
      qc.invalidateQueries({ queryKey: tradingPlanKeys.plan() });
    }
    lastStatusRef.current = current;
  }, [statusView?.status, qc]);

  // Sync the draft from the server-side plan whenever it changes
  // (initial load, regenerate, reset). We deliberately do NOT sync
  // while editing so the user's in-progress changes are not
  // clobbered by a background refetch.
  useEffect(() => {
    if (editing) return;
    if (planRec?.plan) {
      setDraft(planRec.plan);
    } else {
      setDraft(null);
    }
  }, [planRec?.plan, editing]);

  const handleEdit = useCallback(() => {
    if (planRec?.plan) {
      setDraft(planRec.plan);
      setEditing(true);
    }
  }, [planRec?.plan]);

  const handleCancel = useCallback(() => {
    setDraft(planRec?.plan ?? null);
    setEditing(false);
  }, [planRec?.plan]);

  const handleSave = useCallback(() => {
    if (!draft) return;
    update.mutate(draft, {
      onSuccess: () => {
        toast({
          title: 'Plan updated',
          description: 'Your edits are saved.',
          variant: 'success',
        });
        setEditing(false);
      },
      onError: () => {
        toast({
          title: 'Could not save changes',
          description: 'Please review the highlighted fields and try again.',
          variant: 'destructive',
        });
      },
    });
  }, [draft, update]);

  const handleRegenerate = useCallback(() => {
    if (!window.confirm(
      'Regenerate your trading plan? Your current journal entries and edits will be replaced with a fresh AI-generated workbook.',
    )) return;
    generate.mutate(undefined, {
      onSuccess: () => {
        toast({
          title: 'Regenerating plan',
          description: 'A fresh workbook is being generated. The view will update automatically.',
          variant: 'success',
        });
        setEditing(false);
      },
      onError: () => {
        toast({
          title: 'Could not start regeneration',
          description: 'Please try again in a moment.',
          variant: 'destructive',
        });
      },
    });
  }, [generate]);

  const handleExport = useCallback(() => {
    const target = draft ?? planRec?.plan;
    if (!target) return;
    const name = downloadPlanAsExcel(target);
    toast({
      title: 'Plan exported',
      description: `Saved as ${name}.`,
      variant: 'success',
    });
  }, [draft, planRec?.plan]);

  const handleReset = useCallback(() => {
    if (!window.confirm(
      'Reset your trading plan? This clears the workbook entirely. You can generate a new one any time.',
    )) return;
    reset.mutate(undefined, {
      onSuccess: () => {
        toast({
          title: 'Trading plan reset',
          description: 'Generate a new plan when you are ready.',
          variant: 'success',
        });
        setEditing(false);
      },
      onError: () => {
        toast({
          title: 'Could not reset',
          description: 'Please try again in a moment.',
          variant: 'destructive',
        });
      },
    });
  }, [reset]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LogoLoader size={48} />
      </div>
    );
  }

  const status = planRec?.status ?? statusView?.status ?? 'none';
  const lastError = planRec?.last_error ?? statusView?.last_error;
  const hasPlan = !!draft;

  return (
    <div className="flex flex-col gap-4">
      {/* Action bar (only when a plan exists) */}
      {hasPlan && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2">
          <div className="text-xs text-content-muted">
            <span className="font-semibold text-content">Trading Plan</span> · version{' '}
            <span className="tabular-nums text-content">{planRec?.version ?? 0}</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {editing ? (
              <>
                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={update.isPending}
                  className="rounded border border-border bg-app px-3 py-1.5 text-xs font-medium text-content-secondary hover:text-content focus-ring disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={update.isPending}
                  className="rounded bg-brand px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand/90 focus-ring disabled:opacity-60"
                >
                  {update.isPending ? 'Saving…' : 'Save changes'}
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={handleExport}
                  className="rounded border border-border bg-app px-3 py-1.5 text-xs font-medium text-content-secondary hover:text-content focus-ring"
                >
                  Export Excel
                </button>
                <button
                  type="button"
                  onClick={handleRegenerate}
                  disabled={generate.isPending || status === 'generating'}
                  className="rounded border border-border bg-app px-3 py-1.5 text-xs font-medium text-content-secondary hover:text-content focus-ring disabled:opacity-50"
                >
                  Regenerate
                </button>
                <button
                  type="button"
                  onClick={handleEdit}
                  className="rounded bg-brand px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand/90 focus-ring"
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  disabled={reset.isPending}
                  className="rounded border border-border bg-app px-3 py-1.5 text-xs font-medium text-content-secondary hover:text-danger focus-ring disabled:opacity-50"
                >
                  Reset
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Generation states (none / generating / failed all show the banner) */}
      {(status === 'none' || status === 'generating' || status === 'failed') && (
        <GenerateBanner status={status} lastError={lastError} />
      )}

      {/* Plan body — rendered whenever we have a draft, even while a
          regeneration is in-flight, so the user keeps context. */}
      {hasPlan && draft && (
        <>
          <TraderProfileSection value={draft.trader_profile} />
          <AccountParametersSection
            value={draft.account}
            editing={editing}
            onChange={(next) => setDraft({ ...draft, account: next })}
          />
          <JournalSection
            value={draft.journal}
            editing={editing}
            onChange={(next) => setDraft({ ...draft, journal: next })}
          />
          <WeeklyReviewSection value={draft.weekly_review} />
          <ScorecardSection
            value={draft.scorecard}
            editing={editing}
            onChange={(next) => setDraft({ ...draft, scorecard: next })}
          />
          <ObjectivesSection
            value={draft.objectives}
            editing={editing}
            onChange={(next) => setDraft({ ...draft, objectives: next })}
          />
          <FooterMetadata plan={draft} />
        </>
      )}
    </div>
  );
}
