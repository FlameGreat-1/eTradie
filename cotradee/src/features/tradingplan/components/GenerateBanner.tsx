
import { useGenerateTradingPlan } from '../api/hooks';
import { toast } from '@/hooks/useToast';
import type { TradingPlanStatus } from '../types';

interface Props {
  status: TradingPlanStatus;
  lastError?: string;
}

/**
 * Empty / generating / failed state for the Trading Plan view.
 *
 * Surfaces:
 *   - status='none'        — "Generate your plan" CTA
 *   - status='generating'  — progress text
 *   - status='failed'      — error banner + Retry button
 *
 * Includes an optional fallback-balance input so the user can
 * override the broker balance the gateway uses when generating (e.g.
 * during onboarding before the broker is fully provisioned or when
 * the broker reports zero).
 */
export function GenerateBanner({ status, lastError }: Props) {
  const generate = useGenerateTradingPlan();

  const onGenerate = () => {
    generate.mutate({}, {
      onSuccess: () => {
        toast({
          title: 'Plan generation started',
          description: 'This usually takes 10–30 seconds. The view will update automatically.',
          variant: 'success',
        });
      },
      onError: () => {
        toast({
          title: 'Could not start plan generation',
          description: 'Please try again in a moment.',
          variant: 'destructive',
        });
      },
    });
  };

  if (status === 'generating') {
    return (
      <div className="flex flex-col items-center justify-center gap-6 rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-12 text-center shadow-sm">
        <div className="relative flex h-16 w-16 items-center justify-center">
          <div className="absolute inset-0 animate-ping rounded-full bg-brand/20" />
          <span className="relative inline-block h-10 w-10 animate-spin rounded-full border-4 border-brand border-t-transparent shadow-lg shadow-brand/20" />
        </div>
        <div className="space-y-2">
          <h3 className="text-xl font-bold text-black dark:text-white tracking-tight uppercase">Building your plan</h3>
          <p className="text-xs font-medium text-black/40 dark:text-white/40 max-w-sm leading-relaxed">
            Exoper AI is generating your personalised 90-day workbook. Hang tight.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center text-center rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-12 shadow-sm transition-all duration-500">
      {status === 'failed' && lastError && (
        <div className="mb-6 rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-[11px] font-bold text-red-500 tracking-tight leading-relaxed">
          <span className="uppercase text-[9px] font-black tracking-widest bg-red-500/10 px-2 py-0.5 rounded-full mr-2">Error</span>
          {lastError}
        </div>
      )}
      <h3 className="text-xl font-bold text-black dark:text-white tracking-tight">
        {status === 'failed' ? 'Retry generation' : 'Generate your 90-day plan'}
      </h3>
      <p className="mt-2 text-xs font-medium text-black/40 dark:text-white/40 max-w-2xl leading-relaxed mx-auto">
        Exoper AI will build a personalised workbook from your Trading System and your
        current account balance. The plan is exportable to Excel and printable; the
        Exoper analysis engine never uses it.
      </p>

      <div className="mt-8">
        <button
          type="button"
          onClick={onGenerate}
          disabled={generate.isPending}
          className="rounded-xl bg-black dark:bg-white px-8 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40"
        >
          {generate.isPending ? 'Starting…' : status === 'failed' ? 'Retry' : 'Generate plan'}
        </button>
      </div>
    </div>
  );
}
