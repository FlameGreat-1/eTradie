import { useState } from 'react';
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
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [fallbackBalance, setFallbackBalance] = useState('');
  const [fallbackCurrency, setFallbackCurrency] = useState('USD');

  const onGenerate = () => {
    const opts: { fallback_balance?: number; fallback_currency?: string } = {};
    const parsed = parseFloat(fallbackBalance);
    if (Number.isFinite(parsed) && parsed > 0) {
      opts.fallback_balance = parsed;
      opts.fallback_currency = fallbackCurrency.trim() || 'USD';
    }
    generate.mutate(opts, {
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
      <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-border bg-surface p-8 text-center">
        <div className="flex h-10 w-10 items-center justify-center">
          <span className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-content">Building your plan</h3>
          <p className="mt-1 text-sm text-content-muted">
            Exoper AI is generating your personalised 90-day workbook. Hang tight.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-surface p-6 sm:p-8">
      {status === 'failed' && lastError && (
        <div className="mb-4 rounded border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
          <strong className="font-semibold">Last attempt failed.</strong> {lastError}
        </div>
      )}
      <h3 className="text-base font-semibold text-content">
        {status === 'failed' ? 'Retry generation' : 'Generate your 90-day plan'}
      </h3>
      <p className="mt-1 text-sm text-content-muted">
        Exoper AI will build a personalised workbook from your Trading System and your
        current account balance. The plan is exportable to Excel and printable; the
        Exoper analysis engine never uses it.
      </p>

      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <button
          type="button"
          onClick={onGenerate}
          disabled={generate.isPending}
          className="rounded bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand/90 focus-ring disabled:opacity-60"
        >
          {generate.isPending ? 'Starting…' : status === 'failed' ? 'Retry' : 'Generate plan'}
        </button>
        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          className="text-xs font-medium text-content-secondary hover:text-content focus-ring rounded px-2 py-1"
        >
          {showAdvanced ? 'Hide options' : 'Advanced: override balance'}
        </button>
      </div>

      {showAdvanced && (
        <div className="mt-4 grid grid-cols-1 gap-3 rounded border border-border bg-app p-3 sm:grid-cols-2">
          <label className="flex flex-col text-xs font-medium text-content-secondary">
            Fallback balance
            <input
              type="number"
              inputMode="decimal"
              min={0}
              value={fallbackBalance}
              onChange={(e) => setFallbackBalance(e.target.value)}
              placeholder="e.g. 10000"
              className="mt-1 rounded border border-border bg-surface px-2 py-1.5 text-sm font-normal text-content focus-ring"
            />
          </label>
          <label className="flex flex-col text-xs font-medium text-content-secondary">
            Currency
            <input
              type="text"
              value={fallbackCurrency}
              onChange={(e) => setFallbackCurrency(e.target.value.toUpperCase().slice(0, 8))}
              placeholder="USD"
              className="mt-1 rounded border border-border bg-surface px-2 py-1.5 text-sm font-normal text-content focus-ring"
            />
          </label>
          <p className="col-span-1 sm:col-span-2 text-[11px] text-content-muted">
            Used only when your broker has no balance available. Leave blank to use the broker's reported balance.
          </p>
        </div>
      )}
    </div>
  );
}
