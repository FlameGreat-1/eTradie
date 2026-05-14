import type { WeeklyReview } from '../../types';

interface Props {
  value: WeeklyReview;
}

/**
 * Section 4 — Weekly Review.
 *
 * Numbered list of AI-generated reflection prompts. Read-only — the
 * prompts are part of the LLM payload; the trader's answers live in
 * a notebook (or in the exported Excel where each prompt has an
 * empty Answer column the trader fills in).
 */
export function WeeklyReviewSection({ value }: Props) {
  return (
    <section className="rounded-lg border border-border bg-surface p-4 sm:p-5">
      <header className="mb-3">
        <h3 className="text-base font-semibold text-content">Weekly Review</h3>
        <p className="mt-0.5 text-xs text-content-muted">
          Use these prompts every Friday to audit your discipline.
        </p>
      </header>
      <ol className="space-y-2 text-sm">
        {value.prompts.map((p, i) => (
          <li key={`${i}-${p}`} className="flex gap-3">
            <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand/10 text-[11px] font-semibold text-brand">
              {i + 1}
            </span>
            <span className="text-content-secondary">{p}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
