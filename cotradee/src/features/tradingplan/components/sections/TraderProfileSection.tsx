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
    <section className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm">
      <header className="mb-4">
        <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 mb-1">Section 01</div>
        <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Trader Profile</h3>
        <p className="mt-1 text-xs font-medium text-black/40 dark:text-white/40 leading-relaxed">
          AI-generated summary of your unique edge. Regenerate to refresh.
        </p>
      </header>
      <div className="space-y-4">
        <p className="text-sm font-bold text-black dark:text-white leading-relaxed">{value.headline}</p>
        <ul className="space-y-3">
          {value.bullets.map((b, i) => (
            <li
              key={`${i}-${b}`}
              className="flex items-start gap-3 text-sm font-medium text-black/60 dark:text-white/60 leading-relaxed"
            >
              <span aria-hidden className="mt-2 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
              <span>{b}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
