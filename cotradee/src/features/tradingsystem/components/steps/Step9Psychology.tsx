import type { PsychologicalConstraints } from '../../types';
import { StepShell } from '../StepShell';
import { CheckboxToggle } from '../primitives/CheckboxToggle';
import { NumberSlider } from '../primitives/NumberSlider';
import { RadioCardGroup } from '../primitives/RadioCardGroup';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: PsychologicalConstraints;
  onChange: (next: PsychologicalConstraints) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step9Psychology({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  const set = <K extends keyof PsychologicalConstraints>(key: K, v: PsychologicalConstraints[K]) =>
    onChange({ ...value, [key]: v });
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Psychological Constraints"
      description="Behavioural guardrails that protect you from yourself — tilt, revenge trading, overtrading."
    >
      <NumberSlider
        label="Max losses before cooldown"
        description="After this many consecutive losses, the system pauses execution."
        value={value.max_losses_before_cooldown}
        min={0}
        max={10}
        step={1}
        onChange={(v) => set('max_losses_before_cooldown', Math.round(v))}
      />
      <FieldError message={errors['psychology.max_losses_before_cooldown']} />
      <CheckboxToggle
        label="Enforce cooldown after loss streak"
        checked={value.cooldown_after_loss_streak}
        onChange={(v) => set('cooldown_after_loss_streak', v)}
      />
      <CheckboxToggle
        label="Daily lockout after target reached"
        description="Stop trading once you hit your daily profit target."
        checked={value.daily_lockout_after_target}
        onChange={(v) => set('daily_lockout_after_target', v)}
      />
      <CheckboxToggle
        label="Revenge-trading protection"
        description="Block re-entries into the same pair within 30 minutes of a stop-out."
        checked={value.revenge_trading_protection}
        onChange={(v) => set('revenge_trading_protection', v)}
      />
      <CheckboxToggle
        label="Overtrading protection"
        description="Enforce max trades per session and per day."
        checked={value.overtrading_protection}
        onChange={(v) => set('overtrading_protection', v)}
      />
      <div>
        <div className="text-sm font-medium text-content mb-2">Emotional volatility sensitivity</div>
        <RadioCardGroup
          name="emotional_volatility_sensitivity"
          value={value.emotional_volatility_sensitivity}
          onChange={(v) => set('emotional_volatility_sensitivity', v)}
          options={[
            { value: 'low', label: 'Low', description: 'I stay calm under pressure' },
            { value: 'medium', label: 'Medium', description: 'Sometimes I tilt' },
            { value: 'high', label: 'High', description: 'I want strict tilt protection' },
          ]}
        />
        <FieldError message={errors['psychology.emotional_volatility_sensitivity']} />
      </div>
    </StepShell>
  );
}
