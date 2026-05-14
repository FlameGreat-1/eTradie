import type { AutomationPreferences } from '../../types';
import { StepShell } from '../StepShell';
import { RadioCardGroup } from '../primitives/RadioCardGroup';
import { CheckboxToggle } from '../primitives/CheckboxToggle';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: AutomationPreferences;
  onChange: (next: AutomationPreferences) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step11Automation({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  const set = <K extends keyof AutomationPreferences>(key: K, v: AutomationPreferences[K]) =>
    onChange({ ...value, [key]: v });
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Automation"
      description="How much control you delegate to Exoper. You can change this later from Settings."
    >
      <div>
        <div className="text-sm font-medium text-content mb-2">Execution automation mode</div>
        <RadioCardGroup
          name="automation_mode"
          value={value.mode}
          onChange={(v) => set('mode', v)}
          options={[
            { value: 'alert_only', label: 'Alert only', description: 'AI never places orders, just notifies' },
            { value: 'manual_approval', label: 'Manual approval', description: 'You confirm every trade' },
            { value: 'semi_automatic', label: 'Semi-automatic', description: 'AI fires, you can override' },
            { value: 'fully_automatic', label: 'Fully automatic', description: 'AI executes without prompt' },
          ]}
        />
        <FieldError message={errors['automation.mode']} />
      </div>
      <CheckboxToggle
        label="Require final user confirmation"
        description="Even with semi/fully automatic, Exoper waits for your tap before firing."
        checked={value.require_final_confirmation}
        onChange={(v) => set('require_final_confirmation', v)}
      />
      <FieldError message={errors['automation.require_final_confirmation']} />
      <CheckboxToggle
        label="Allow unattended execution"
        description="Allow Exoper to fire trades when you are not logged in."
        checked={value.allow_unattended_execution}
        onChange={(v) => set('allow_unattended_execution', v)}
      />
    </StepShell>
  );
}
