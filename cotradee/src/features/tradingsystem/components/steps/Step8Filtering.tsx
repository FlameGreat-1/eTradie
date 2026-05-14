import type { TradeFiltering } from '../../types';
import { StepShell } from '../StepShell';
import { CheckboxToggle } from '../primitives/CheckboxToggle';
import { NumberSlider } from '../primitives/NumberSlider';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: TradeFiltering;
  onChange: (next: TradeFiltering) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step8Filtering({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  const set = <K extends keyof TradeFiltering>(key: K, v: TradeFiltering[K]) =>
    onChange({ ...value, [key]: v });
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Trade Filtering"
      description="Setups Exoper should automatically discard, even when other confluence is present."
    >
      <NumberSlider
        label="Minimum reward-to-risk"
        description="Reject any setup with an RR below this floor."
        value={value.minimum_rr}
        min={1.0}
        max={10.0}
        step={0.1}
        suffix=":1"
        onChange={(v) => set('minimum_rr', v)}
      />
      <FieldError message={errors['filtering.minimum_rr']} />
      <CheckboxToggle
        label="Avoid counter-trend setups"
        checked={value.avoid_counter_trend}
        onChange={(v) => set('avoid_counter_trend', v)}
      />
      <CheckboxToggle
        label="Avoid news volatility"
        description="Skip setups within 30 minutes of high-impact news."
        checked={value.avoid_news_volatility}
        onChange={(v) => set('avoid_news_volatility', v)}
      />
      <CheckboxToggle
        label="Avoid ranging markets"
        checked={value.avoid_ranging_markets}
        onChange={(v) => set('avoid_ranging_markets', v)}
      />
      <CheckboxToggle
        label="Avoid overnight holds"
        description="Close positions before the daily session close."
        checked={value.avoid_overnight_holds}
        onChange={(v) => set('avoid_overnight_holds', v)}
      />
      <CheckboxToggle
        label="Avoid Friday trades"
        description="Weekend gap risk protection."
        checked={value.avoid_friday_trades}
        onChange={(v) => set('avoid_friday_trades', v)}
      />
      <CheckboxToggle
        label="Avoid session transitions"
        description="Skip the first 15 minutes of every new session."
        checked={value.avoid_session_transitions}
        onChange={(v) => set('avoid_session_transitions', v)}
      />
    </StepShell>
  );
}
