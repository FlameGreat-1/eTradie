import type { EntryPreferences } from '../../types';
import { StepShell } from '../StepShell';
import { RadioCardGroup } from '../primitives/RadioCardGroup';
import { CheckboxToggle } from '../primitives/CheckboxToggle';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: EntryPreferences;
  onChange: (next: EntryPreferences) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step7Entry({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Entry Preferences"
      description="How and when the AI should fire the entry order."
    >
      <div>
        <div className="text-sm font-medium text-content mb-2">Execution mode</div>
        <RadioCardGroup
          name="execution_mode"
          value={value.execution_mode}
          onChange={(v) => onChange({ ...value, execution_mode: v })}
          options={[
            { value: 'limit_only', label: 'Limit only', description: 'Pre-positioned at the zone' },
            { value: 'market_allowed', label: 'Market only', description: 'Enter on confirmation candle' },
            { value: 'either_allowed', label: 'Either', description: 'AI picks per setup' },
          ]}
        />
        <FieldError message={errors['entry.execution_mode']} />
      </div>

      <CheckboxToggle
        label="Require confirmation candle"
        description="Wait for a closing candle that confirms the setup before firing."
        checked={value.require_confirmation_candle}
        onChange={(v) => onChange({ ...value, require_confirmation_candle: v })}
      />
      <CheckboxToggle
        label="Require retest"
        description="Only enter on a retest of the broken structure."
        checked={value.require_retest}
        onChange={(v) => onChange({ ...value, require_retest: v })}
      />
      <CheckboxToggle
        label="Require liquidity sweep"
        description="Setup must be preceded by a sweep of opposite liquidity."
        checked={value.require_liquidity_sweep}
        onChange={(v) => onChange({ ...value, require_liquidity_sweep: v })}
      />
      <CheckboxToggle
        label="Require multi-timeframe alignment"
        description="HTF, MTF, and LTF must all agree on direction."
        checked={value.require_mtf_alignment}
        onChange={(v) => onChange({ ...value, require_mtf_alignment: v })}
      />
    </StepShell>
  );
}
