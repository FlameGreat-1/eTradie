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
  type TradingPlanStatus,
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
  const lastStatusRef = useRef<TradingPlanStatus | undefined>(undefined);
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
    <div className="flex flex-col gap-6 pb-20">
      {/* Action bar (only when a plan exists) */}
      {hasPlan && (
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] px-6 py-4 shadow-sm backdrop-blur-sm transition-all duration-300">
          <div className="flex flex-col gap-1">
            <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/40 dark:text-white/40">
              Active Strategy
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-black dark:text-white tracking-tight">Trading Plan</span>
              <span className="h-1 w-1 rounded-full bg-black/20 dark:bg-white/20" />
              <span className="text-xs font-black text-brand uppercase tracking-widest bg-brand/10 px-2 py-0.5 rounded-full">
                v{planRec?.version ?? 0}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {editing ? (
              <>
                <button
                  type="button"
                  onClick={handleCancel}
                  disabled={update.isPending}
                  className="rounded-xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white hover:border-black/30 dark:hover:border-white/30 transition-all disabled:opacity-20"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={update.isPending}
                  className="rounded-xl bg-black dark:bg-white px-6 py-2.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40"
                >
                  {update.isPending ? 'Saving…' : 'Save changes'}
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={handleExport}
                  className="rounded-xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white hover:border-black/30 dark:hover:border-white/30 transition-all"
                >
                  Export Excel
                </button>
                <button
                  type="button"
                  onClick={handleRegenerate}
                  disabled={generate.isPending || status === 'generating'}
                  className="rounded-xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white hover:border-black/30 dark:hover:border-white/30 transition-all disabled:opacity-20"
                >
                  Regenerate
                </button>
                <button
                  type="button"
                  onClick={handleEdit}
                  className="rounded-xl bg-black dark:bg-white px-8 py-2.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all"
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  disabled={reset.isPending}
                  className="rounded-xl border border-red-500/20 bg-red-500/5 px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-red-500/60 hover:text-red-500 hover:border-red-500/40 transition-all disabled:opacity-20"
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
