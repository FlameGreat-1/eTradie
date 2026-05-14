import type { AssetPreferences } from '../../types';
import { StepShell } from '../StepShell';
import { MultiSelectChips } from '../primitives/MultiSelectChips';
import { CheckboxToggle } from '../primitives/CheckboxToggle';
import { TagInput } from '../primitives/TagInput';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: AssetPreferences;
  onChange: (next: AssetPreferences) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step12Assets({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Asset Preferences"
      description="The asset classes you want the AI to analyse for you, plus optional pinned pairs."
    >
      <div>
        <div className="text-sm font-medium text-content mb-2">Asset classes</div>
        <MultiSelectChips
          name="asset_classes"
          value={value.asset_classes}
          minCount={1}
          onChange={(v) => onChange({ ...value, asset_classes: v })}
          options={[
            { value: 'forex', label: 'Forex' },
            { value: 'indices', label: 'Indices' },
            { value: 'gold', label: 'Gold' },
            { value: 'crypto', label: 'Crypto' },
            { value: 'volatility_indices', label: 'Volatility Indices' },
          ]}
        />
        <FieldError message={errors['assets.asset_classes']} />
      </div>
      <TagInput
        label="Preferred pairs (optional)"
        description="Pinned symbols the AI should prioritise. Enter or comma to add."
        value={value.preferred_pairs}
        onChange={(v) => onChange({ ...value, preferred_pairs: v })}
      />
      <FieldError message={errors['assets.preferred_pairs']} />
      <CheckboxToggle
        label="Avoid highly volatile instruments"
        checked={value.avoid_highly_volatile}
        onChange={(v) => onChange({ ...value, avoid_highly_volatile: v })}
      />
      <CheckboxToggle
        label="Avoid correlated instruments simultaneously"
        description="Block opening EURUSD + GBPUSD or XAUUSD + silver at the same time."
        checked={value.avoid_correlated_instruments}
        onChange={(v) => onChange({ ...value, avoid_correlated_instruments: v })}
      />
    </StepShell>
  );
}
