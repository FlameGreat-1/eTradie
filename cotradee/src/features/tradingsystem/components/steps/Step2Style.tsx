import type { TradingStyle } from '../../types';
import { StepShell } from '../StepShell';
import { RadioCardGroup } from '../primitives/RadioCardGroup';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: TradingStyle;
  onChange: (next: TradingStyle) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step2Style({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Trading Style"
      description="Your operating style determines which timeframes the AI prioritises and how long trades typically run."
    >
      <RadioCardGroup
        name="style"
        value={value}
        onChange={onChange}
        options={[
          { value: 'scalping', label: 'Scalping', description: 'Minutes to an hour (M1–M15)' },
          { value: 'intraday', label: 'Intraday', description: 'Hours within a session (M15–H4)' },
          { value: 'swing', label: 'Swing', description: 'Days to a week (H4–D1)' },
          { value: 'positional', label: 'Positional', description: 'Weeks to months (D1–W1)' },
        ]}
      />
      <FieldError message={errors['style']} />
    </StepShell>
  );
}
