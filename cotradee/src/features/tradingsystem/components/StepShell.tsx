import { type ReactNode } from 'react';
import { SectionHeader } from './primitives/SectionHeader';

interface Props {
  stepNumber: number;
  totalSteps: number;
  title: string;
  description: string;
  children: ReactNode;
}

/**
 * Wraps each step's content with a uniform header so the visual
 * rhythm is identical across all 14 sections.
 */
export function StepShell({ stepNumber, totalSteps, title, description, children }: Props) {
  return (
    <div className="space-y-4">
      <SectionHeader
        title={title}
        description={description}
        stepNumber={stepNumber}
        totalSteps={totalSteps}
      />
      <div className="space-y-3">{children}</div>
    </div>
  );
}
