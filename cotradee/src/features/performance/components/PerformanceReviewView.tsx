import { useMemo, useState } from 'react';
import { Calendar, CalendarDays, History as HistoryIcon, RefreshCcw } from 'lucide-react';
import { toast } from '@/hooks/useToast';
import {
  useGeneratePerformanceReview,
  usePerformanceReviewLatest,
} from '../api/hooks';
import type { PerformanceReviewPeriod } from '../types';
import { EmptyReviewState, FailureBanner, GenerationBanner } from './GenerationBanner';
import { PerformanceReviewSections } from './PerformanceReviewSections';
import { PerformanceReviewHistory } from './PerformanceReviewHistory';

type Tab = PerformanceReviewPeriod | 'history';

/**
 * Top-level Performance Review view rendered by the dashboard page.
 *
 * Layout:
 *   1. Tab switcher: Weekly | Monthly | History (sticky on mobile).
 *   2. Header row with period range + 'Run review now' CTA + confidence badge.
 *   3. Banner row (generation in flight, failure with retry, or empty CTA).
 *   4. 14-section grid (delivered by PerformanceReviewSections).
 *   5. History view (delivered by PerformanceReviewHistory) when that tab is active.
 *
 * Rendering modes:
 *   - status='generating' — GenerationBanner + previous review beneath if any.
 *   - status='failed'     — FailureBanner + previous review beneath if any.
 *   - status='ready'      — full 14-section grid.
 *   - status='none'       — EmptyReviewState card.
 */
export function PerformanceReviewView() {
  const [tab, setTab] = useState<Tab>('weekly');
  const period: PerformanceReviewPeriod = tab === 'history' ? 'weekly' : tab;

  const { data: latest, isLoading } = usePerformanceReviewLatest(period);
  const generate = useGeneratePerformanceReview();

  const handleGenerate = (p: PerformanceReviewPeriod) => {
    generate.mutate(p, {
      onSuccess: () =>
        toast({
          title: 'Review queued',
          description: 'Your performance review is being generated.',
        }),
      onError: (err: unknown) => {
        const message =
          (err as { response?: { data?: { error?: string } } })?.response?.data?.error ??
          'Could not start review generation.';
        toast({ title: 'Generation failed', description: message, variant: 'destructive' });
      },
    });
  };

  const windowLabel = useMemo(() => formatWindow(latest?.period_start, latest?.period_end), [
    latest?.period_start,
    latest?.period_end,
  ]);

  return (
    <div className="flex flex-col gap-4 sm:gap-5 max-w-5xl mx-auto w-full pb-12">
      <Tabs tab={tab} setTab={setTab} />

      {tab === 'history' ? (
        <PerformanceReviewHistory />
      ) : (
        <>
          <HeaderRow
            period={period}
            windowLabel={windowLabel}
            isGenerating={generate.isPending}
            onGenerate={() => handleGenerate(period)}
          />

          {isLoading ? (
            <SkeletonGrid />
          ) : !latest || latest.status === 'none' ? (
            <EmptyReviewState
              period={period}
              onGenerate={() => handleGenerate(period)}
              isGenerating={generate.isPending}
            />
          ) : (
            <>
              {latest.status === 'generating' && (
                <GenerationBanner period={period} />
              )}
              {latest.status === 'failed' && (
                <FailureBanner
                  period={period}
                  message={latest.last_error || 'Generation failed.'}
                  onRegenerate={() => handleGenerate(period)}
                  isRegenerating={generate.isPending}
                />
              )}
              {latest.review && (
                <PerformanceReviewSections review={latest.review} />
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

function Tabs({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const items: { id: Tab; label: string; icon: typeof Calendar }[] = [
    { id: 'weekly', label: 'Weekly', icon: Calendar },
    { id: 'monthly', label: 'Monthly', icon: CalendarDays },
    { id: 'history', label: 'History', icon: HistoryIcon },
  ];
  return (
    <div
      role="tablist"
      aria-label="Performance review periods"
      className="sticky top-0 z-10 flex items-center gap-1 p-1 rounded-2xl bg-black/[0.03] dark:bg-white/[0.03] backdrop-blur"
    >
      {items.map(({ id, label, icon: Icon }) => {
        const active = tab === id;
        return (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => setTab(id)}
            className={`flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all focus-ring
              ${
                active
                  ? 'bg-white dark:bg-black text-black dark:text-white shadow-sm'
                  : 'text-black/50 dark:text-white/50 hover:text-black dark:hover:text-white'
              }`}
          >
            <Icon size={14} aria-hidden />
            <span>{label}</span>
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// HeaderRow
// ---------------------------------------------------------------------------

function HeaderRow({
  period,
  windowLabel,
  isGenerating,
  onGenerate,
}: {
  period: PerformanceReviewPeriod;
  windowLabel: string;
  isGenerating: boolean;
  onGenerate: () => void;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
      <div>
        <h1 className="text-lg sm:text-xl font-bold tracking-tight text-black dark:text-white">
          {period === 'weekly' ? 'Weekly performance review' : 'Monthly performance review'}
        </h1>
        <p className="mt-0.5 text-xs sm:text-sm font-medium text-black/50 dark:text-white/50">
          {windowLabel || 'No window yet.'}
        </p>
      </div>
      <button
        type="button"
        onClick={onGenerate}
        disabled={isGenerating}
        className="shrink-0 inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold
                   bg-black dark:bg-white text-white dark:text-black hover:opacity-90
                   disabled:opacity-60 disabled:cursor-not-allowed transition-opacity focus-ring"
      >
        <RefreshCcw size={14} aria-hidden className={isGenerating ? 'animate-spin' : ''} />
        Run review now
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton (rendered while the latest fetch is in-flight on first paint)
// ---------------------------------------------------------------------------

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">
      {Array.from({ length: 6 }).map((_, idx) => (
        <div
          key={idx}
          className="h-48 rounded-2xl bg-black/[0.03] dark:bg-white/[0.03] animate-pulse"
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatWindow(start?: string, end?: string): string {
  if (!start || !end) return '';
  try {
    const s = new Date(start);
    const e = new Date(end);
    const fmt: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', year: 'numeric' };
    return `${s.toLocaleDateString(undefined, fmt)} \u2013 ${e.toLocaleDateString(undefined, fmt)}`;
  } catch {
    return '';
  }
}
