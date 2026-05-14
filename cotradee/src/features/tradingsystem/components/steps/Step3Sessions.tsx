import type { SessionPreferences } from '../../types';
import { StepShell } from '../StepShell';
import { MultiSelectChips } from '../primitives/MultiSelectChips';
import { CheckboxToggle } from '../primitives/CheckboxToggle';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: SessionPreferences;
  onChange: (next: SessionPreferences) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step3Sessions({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Session Preferences"
      description="Trading sessions you participate in. Pick at least one; the AI will weight setups in your chosen windows higher."
    >
      <div>
        <div className="text-sm font-medium text-content mb-2">Preferred sessions</div>
        <MultiSelectChips
          name="preferred_sessions"
          value={value.preferred_sessions}
          minCount={1}
          onChange={(v) => onChange({ ...value, preferred_sessions: v })}
          options={[
            { value: 'asian', label: 'Asian' },
            { value: 'london', label: 'London' },
            { value: 'new_york', label: 'New York' },
            { value: 'london_ny_overlap', label: 'London/NY Overlap' },
          ]}
        />
        <FieldError message={errors['sessions.preferred_sessions']} />
      </div>

      <CheckboxToggle
        label="Avoid low-liquidity periods"
        description="Skip mid-Asian doldrums and pre-London rollover when spread widens."
        checked={value.avoid_low_liquidity}
        onChange={(v) => onChange({ ...value, avoid_low_liquidity: v })}
      />
      <CheckboxToggle
        label="Only trade high-volatility windows"
        description="Restrict execution to the most active hours of each chosen session."
        checked={value.high_volatility_windows_only}
        onChange={(v) => onChange({ ...value, high_volatility_windows_only: v })}
      />
    </StepShell>
  );
}
