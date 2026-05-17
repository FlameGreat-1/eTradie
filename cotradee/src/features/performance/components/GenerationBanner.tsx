import { AlertTriangle, Loader2, RefreshCcw } from 'lucide-react';
import type { PerformanceReviewPeriod } from '../types';

/**
 * Banner rendered above the review when the row is in transient
 * states. Visually subdued so it never competes with the review
 * content beneath when a previous successful run is still rendered
 * underneath (the gateway preserves history; nothing flashes blank).
 */
interface GenerationBannerProps {
  period: PerformanceReviewPeriod;
  message?: string;
}

export function GenerationBanner({ period, message }: GenerationBannerProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-3 px-4 sm:px-5 py-3 rounded-2xl border border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02]"
    >
      <Loader2 size={16} className="animate-spin text-black/60 dark:text-white/60 shrink-0" aria-hidden />
      <div className="min-w-0">
        <p className="text-xs sm:text-sm font-bold text-black dark:text-white">
          Generating your {period} performance review
        </p>
        <p className="mt-0.5 text-[11px] sm:text-xs text-black/50 dark:text-white/50 truncate">
          {message || 'Analyzing your trade history against your trading system. This typically takes 20\u201360 seconds.'}
        </p>
      </div>
    </div>
  );
}

interface FailureBannerProps {
  period: PerformanceReviewPeriod;
  message: string;
  onRegenerate: () => void;
  isRegenerating: boolean;
}

export function FailureBanner({
  period,
  message,
  onRegenerate,
  isRegenerating,
}: FailureBannerProps) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 px-4 sm:px-5 py-3 rounded-2xl border border-rose-500/20 bg-rose-500/5"
    >
      <AlertTriangle size={16} className="text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-xs sm:text-sm font-bold text-rose-700 dark:text-rose-300">
          The last {period} review could not be generated
        </p>
        <p className="mt-0.5 text-[11px] sm:text-xs text-rose-600/80 dark:text-rose-400/80 break-words">
          {message || 'Please try again.'}
        </p>
      </div>
      <button
        type="button"
        onClick={onRegenerate}
        disabled={isRegenerating}
        className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] sm:text-xs font-bold
                   bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-60 disabled:cursor-not-allowed
                   transition-colors focus-ring"
      >
        <RefreshCcw size={12} aria-hidden className={isRegenerating ? 'animate-spin' : ''} />
        Try again
      </button>
    </div>
  );
}

interface EmptyReviewStateProps {
  period: PerformanceReviewPeriod;
  onGenerate: () => void;
  isGenerating: boolean;
}

export function EmptyReviewState({ period, onGenerate, isGenerating }: EmptyReviewStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-12 px-6 rounded-2xl border border-dashed border-black/10 dark:border-white/10 text-center">
      <div className="w-12 h-12 rounded-2xl bg-black/5 dark:bg-white/5 flex items-center justify-center" aria-hidden>
        <Loader2 size={20} className="text-black/40 dark:text-white/40" />
      </div>
      <div>
        <h3 className="text-sm sm:text-base font-bold text-black dark:text-white">
          No {period} review yet
        </h3>
        <p className="mt-1 text-xs sm:text-sm text-black/50 dark:text-white/50 max-w-md">
          Exoper AI will analyze your trade history against your trading system and produce
          a calm, structured performance review.
        </p>
      </div>
      <button
        type="button"
        onClick={onGenerate}
        disabled={isGenerating}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold
                   bg-black dark:bg-white text-white dark:text-black hover:opacity-90
                   disabled:opacity-60 disabled:cursor-not-allowed transition-opacity focus-ring"
      >
        {isGenerating && <Loader2 size={14} className="animate-spin" aria-hidden />}
        Generate review
      </button>
    </div>
  );
}
