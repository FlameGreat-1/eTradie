import { memo } from 'react';

interface Props {
  title: string;
  description: string;
  stepNumber: number;
  totalSteps: number;
}

/**
 * Consistent step header. Renders the step counter, title, and the
  * short "why this matters" blurb so the builder feels guided rather
  * than a wall of questions.
 */
function SectionHeaderInner({ title, description, stepNumber, totalSteps }: Props) {
  return (
    <header className="mb-6 text-center">
      <h2 className="text-xl font-bold text-black dark:text-white tracking-tight leading-none">{title}</h2>
      <p className="mt-1.5 text-[11px] text-black/50 dark:text-white/50 leading-normal max-w-xl mx-auto">{description}</p>
      <div className="mt-3 inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-brand/10 border border-brand/20">
        <span className="text-[9px] font-black text-brand uppercase tracking-widest">
          Step {stepNumber} of {totalSteps}
        </span>
      </div>
    </header>
  );
}

export const SectionHeader = memo(SectionHeaderInner);
