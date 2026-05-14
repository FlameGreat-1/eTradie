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
    <header className="mb-4">
      <div className="text-xs uppercase tracking-wide text-content-muted mb-1">
        Step {stepNumber} of {totalSteps}
      </div>
      <h2 className="text-lg font-semibold text-content">{title}</h2>
      <p className="mt-1 text-sm text-content-secondary">{description}</p>
    </header>
  );
}

export const SectionHeader = memo(SectionHeaderInner);
