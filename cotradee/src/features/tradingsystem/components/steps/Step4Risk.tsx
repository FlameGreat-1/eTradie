import type { RiskPersonality } from '../../types';
import { StepShell } from '../StepShell';
import { RadioCardGroup } from '../primitives/RadioCardGroup';
import { CheckboxToggle } from '../primitives/CheckboxToggle';
import { NumberSlider } from '../primitives/NumberSlider';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: RiskPersonality;
  onChange: (next: RiskPersonality) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step4Risk({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  const set = <K extends keyof RiskPersonality>(key: K, v: RiskPersonality[K]) =>
    onChange({ ...value, [key]: v });

  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Risk Personality"
      description="How much capital you risk per trade and the drawdown limits Exoper must respect."
    >
      <div className="space-y-8">
        <div>
          <div className="text-[10px] text-black/30 dark:text-white/30 uppercase font-bold tracking-[0.15em] mb-3">1. Risk model</div>
          <RadioCardGroup
            name="risk_model"
            value={value.risk_model}
            onChange={(v) => set('risk_model', v)}
            options={[
              { value: 'fixed', label: 'Fixed %', description: 'Same % per trade always' },
              { value: 'adaptive', label: 'Adaptive %', description: 'Scaled by setup grade' },
            ]}
          />
          <FieldError message={errors['risk.risk_model']} />
        </div>

      <NumberSlider
        label="Risk per trade"
        description="Percentage of account equity risked on each position."
        value={value.fixed_risk_percent}
        min={0.1}
        max={3.0}
        step={0.1}
        suffix="%"
        onChange={(v) => set('fixed_risk_percent', v)}
      />
      <FieldError message={errors['risk.fixed_risk_percent']} />

      <NumberSlider
        label="Max daily drawdown"
        description="Stop trading for the day when reached."
        value={value.max_daily_drawdown_percent}
        min={1.0}
        max={10.0}
        step={0.5}
        suffix="%"
        onChange={(v) => set('max_daily_drawdown_percent', v)}
      />
      <FieldError message={errors['risk.max_daily_drawdown_percent']} />

      <NumberSlider
        label="Max weekly drawdown"
        description="Stop trading for the week when reached."
        value={value.max_weekly_drawdown_percent}
        min={2.0}
        max={20.0}
        step={0.5}
        suffix="%"
        onChange={(v) => set('max_weekly_drawdown_percent', v)}
      />
      <FieldError message={errors['risk.max_weekly_drawdown_percent']} />

      <NumberSlider
        label="Max simultaneous trades"
        description="Open positions at any one time."
        value={value.max_simultaneous_trades}
        min={1}
        max={10}
        step={1}
        onChange={(v) => set('max_simultaneous_trades', Math.round(v))}
      />
      <FieldError message={errors['risk.max_simultaneous_trades']} />

      <NumberSlider
        label="Max correlated exposure"
        description="Open positions in correlated instruments."
        value={value.max_correlated_exposure}
        min={1}
        max={5}
        step={1}
        onChange={(v) => set('max_correlated_exposure', Math.round(v))}
      />
      <FieldError message={errors['risk.max_correlated_exposure']} />

      <CheckboxToggle
        label="Partial take profits"
        description="Close part of the position at TP1 to lock in profit."
        checked={value.partial_take_profits}
        onChange={(v) => set('partial_take_profits', v)}
      />
      <CheckboxToggle
        label="Break-even management"
        description="Move SL to break-even once price reaches TP1."
        checked={value.break_even_management}
        onChange={(v) => set('break_even_management', v)}
      />
      <CheckboxToggle
        label="Trailing stop"
        description="Trail the stop loss as the trade progresses."
        checked={value.trailing_stop_enabled}
        onChange={(v) => set('trailing_stop_enabled', v)}
      />
      </div>
    </StepShell>
  );
}
