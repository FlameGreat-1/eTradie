import type { TraderProfile } from '../../types';

interface Props {
  value: TraderProfile;
}

/**
 * Section 1 — Trader Profile.
 *
 * Read-only. The LLM owns this section: the headline and bullets are
 * a synthesis of the user's saved Trading System and are refreshed
 * only when the user regenerates the plan. The PRACTICE.md spec is
 * explicit that this section is a narrative summary, not a parameter
 * table the trader fills in.
 */
export function TraderProfileSection({ value }: Props) {
  return (
    <section className="rounded-lg border border-border bg-surface p-4 sm:p-5">
      <header className="mb-3">
        <h3 className="text-base font-semibold text-content">Trader Profile</h3>
        <p className="mt-0.5 text-xs text-content-muted">
          AI-generated summary of how you trade. Regenerate to refresh.
        </p>
      </header>
      <p className="text-sm font-medium text-content">{value.headline}</p>
      <ul className="mt-3 space-y-1.5">
        {value.bullets.map((b, i) => (
          <li
            key={`${i}-${b}`}
            className="flex items-start gap-2 text-sm text-content-secondary"
          >
            <span aria-hidden className="mt-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
            <span>{b}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
