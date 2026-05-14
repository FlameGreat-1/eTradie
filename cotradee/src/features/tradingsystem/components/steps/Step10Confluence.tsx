import type { ConfluenceWeights } from '../../types';
import { StepShell } from '../StepShell';
import { WeightSlider } from '../primitives/WeightSlider';

interface Props {
  value: ConfluenceWeights;
  onChange: (next: ConfluenceWeights) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step10Confluence({ value, onChange, stepNumber, totalSteps }: Props) {
  const set = <K extends keyof ConfluenceWeights>(key: K, v: number) =>
    onChange({ ...value, [key]: Math.max(0, Math.min(3, Math.round(v))) });
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Confluence Preferences"
      description="How much weight the AI should give to each confluence factor when scoring setups. The institutional rulebook still enforces mandatory factors regardless."
    >
      <WeightSlider
        label="Macro alignment"
        description="Central-bank stance, rate differentials, economic surprises."
        value={value.macro_alignment}
        onChange={(v) => set('macro_alignment', v)}
      />
      <WeightSlider
        label="DXY (US Dollar Index)"
        description="USD strength bias against your traded pair."
        value={value.dxy}
        onChange={(v) => set('dxy', v)}
      />
      <WeightSlider
        label="COT positioning"
        description="Commercial vs speculative net positioning."
        value={value.cot}
        onChange={(v) => set('cot', v)}
      />
      <WeightSlider
        label="HTF alignment"
        description="Higher-timeframe trend agreement with the setup."
        value={value.htf_alignment}
        onChange={(v) => set('htf_alignment', v)}
      />
      <WeightSlider
        label="Wyckoff phase"
        description="Accumulation / distribution context."
        value={value.wyckoff}
        onChange={(v) => set('wyckoff', v)}
      />
      <WeightSlider
        label="Volume / liquidity"
        description="Liquidity pools and volume spikes."
        value={value.volume_liquidity}
        onChange={(v) => set('volume_liquidity', v)}
      />
      <WeightSlider
        label="Session timing"
        description="Whether the setup formed in a preferred session window."
        value={value.session_timing}
        onChange={(v) => set('session_timing', v)}
      />
    </StepShell>
  );
}
