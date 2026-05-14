import type { ConfirmationStrictness } from '../../types';
import { StepShell } from '../StepShell';
import { RadioCardGroup } from '../primitives/RadioCardGroup';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: ConfirmationStrictness;
  onChange: (next: ConfirmationStrictness) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step5Confirmation({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Confirmation Strictness"
      description="How much evidence the AI needs before flagging a setup as tradeable."
    >
      <RadioCardGroup
        name="confirmation"
        value={value}
        onChange={onChange}
        options={[
          { value: 'aggressive', label: 'Aggressive', description: 'Enter early on first signal' },
          { value: 'balanced', label: 'Balanced', description: 'Wait for primary confirmation' },
          { value: 'strict', label: 'Strict', description: 'Multiple confirmations required' },
        ]}
      />
      <FieldError message={errors['confirmation']} />
    </StepShell>
  );
}
