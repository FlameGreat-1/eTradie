import type { GoalOrientation } from '../../types';
import { StepShell } from '../StepShell';
import { RadioCardGroup } from '../primitives/RadioCardGroup';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: GoalOrientation;
  onChange: (next: GoalOrientation) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step13Goal({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Goal Orientation"
      description="The single guiding objective that shapes how Exoper ranks trade-offs."
    >
      <div className="space-y-8">
        <div>
          <div className="text-[10px] text-black/30 dark:text-white/30 uppercase font-bold tracking-[0.15em] mb-3">Goal orientation</div>
      <RadioCardGroup
        name="goal"
        value={value}
        onChange={onChange}
        options={[
          { value: 'capital_preservation', label: 'Capital preservation', description: 'Lose as little as possible' },
          { value: 'consistency', label: 'Consistency', description: 'Steady win rate, low variance' },
          { value: 'aggressive_growth', label: 'Aggressive growth', description: 'Maximise returns, accept volatility' },
          { value: 'low_stress', label: 'Low stress', description: 'Few high-quality trades, sleep well' },
          { value: 'high_probability_only', label: 'High-probability only', description: 'A+ setups exclusively' },
          { value: 'fewer_high_quality', label: 'Fewer, higher-quality', description: 'Quality over quantity' },
        ]}
      />
      <FieldError message={errors['goal']} />
      </div>
      </div>
    </StepShell>
  );
}
