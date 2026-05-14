import type { StructuralPreferences } from '../../types';
import { StepShell } from '../StepShell';
import { MultiSelectChips } from '../primitives/MultiSelectChips';
import { CheckboxToggle } from '../primitives/CheckboxToggle';
import { RadioCardGroup } from '../primitives/RadioCardGroup';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: StructuralPreferences;
  onChange: (next: StructuralPreferences) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step6Structural({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Structural Preferences"
      description="The structural frameworks and patterns you want Exoper to prioritise in retrieval."
    >
      <div>
        <div className="text-sm font-medium text-content mb-2">Structural frameworks</div>
        <MultiSelectChips
          name="frameworks"
          value={value.frameworks}
          minCount={1}
          onChange={(v) => onChange({ ...value, frameworks: v })}
          options={[
            { value: 'smc', label: 'SMC' },
            { value: 'snd', label: 'Supply & Demand' },
            { value: 'wyckoff', label: 'Wyckoff' },
            { value: 'liquidity', label: 'Liquidity concepts' },
          ]}
        />
        <FieldError message={errors['structural.frameworks']} />
      </div>

      <CheckboxToggle
        label="Use Fair Value Gaps (FVG)"
        checked={value.use_fvg}
        onChange={(v) => onChange({ ...value, use_fvg: v })}
      />
      <CheckboxToggle
        label="Use Order Blocks"
        checked={value.use_order_blocks}
        onChange={(v) => onChange({ ...value, use_order_blocks: v })}
      />
      <CheckboxToggle
        label="Use CHoCH / BMS confirmation"
        description="Require Change of Character or Break of Market Structure events."
        checked={value.use_choch_bms}
        onChange={(v) => onChange({ ...value, use_choch_bms: v })}
      />
      <CheckboxToggle
        label="Use IDM (inducement) confirmation"
        description="Require evidence of inducement before entry."
        checked={value.use_idm}
        onChange={(v) => onChange({ ...value, use_idm: v })}
      />

      <div>
        <div className="text-sm font-medium text-content mb-2">Structure emphasis</div>
        <RadioCardGroup
          name="structure_emphasis"
          value={value.structure_emphasis}
          onChange={(v) => onChange({ ...value, structure_emphasis: v })}
          options={[
            { value: 'low', label: 'Low', description: 'Structure is one factor among many' },
            { value: 'medium', label: 'Medium', description: 'Balanced with macro / liquidity' },
            { value: 'high', label: 'High', description: 'Structure leads every decision' },
          ]}
        />
        <FieldError message={errors['structural.structure_emphasis']} />
      </div>
    </StepShell>
  );
}
