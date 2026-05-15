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
    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <SectionHeader
        title={title}
        description={description}
        stepNumber={stepNumber}
        totalSteps={totalSteps}
      />
      <div className="w-full max-w-3xl mx-auto">{children}</div>
    </div>
  );
}
