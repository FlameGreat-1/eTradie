import type { WeeklyReview } from '../../types';

interface Props {
  value: WeeklyReview;
  headerActions?: React.ReactNode;
}

/**
 * Section 4 — Weekly Review.
 *
 * Numbered list of AI-generated reflection prompts. Read-only — the
 * prompts are part of the LLM payload; the trader's answers live in
 * a notebook (or in the exported Excel where each prompt has an
 * empty Answer column the trader fills in).
 */
export function WeeklyReviewSection({ value, headerActions }: Props) {
  return (
    <section className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm">
      <header className="mb-4 flex items-start justify-between gap-2 sm:gap-4">
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 mb-1">Section 04</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Weekly Review</h3>
          <p className="mt-1 text-[10px] sm:text-xs font-medium text-black/40 dark:text-white/40 leading-relaxed">
            Use these prompts every Friday to audit your discipline.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {headerActions}
        </div>
      </header>
      <ol className="space-y-4">
        {value.prompts.map((p, i) => (
          <li key={`${i}-${p}`} className="flex gap-4">
            <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 text-[10px] font-black text-black dark:text-white">
              {String(i + 1).padStart(2, '0')}
            </span>
            <span className="text-sm font-medium text-black/60 dark:text-white/60 leading-relaxed">{p}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
