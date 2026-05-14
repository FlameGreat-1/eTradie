import type { TradeManagement } from '../../types';
import { StepShell } from '../StepShell';
import { RadioCardGroup } from '../primitives/RadioCardGroup';
import { CheckboxToggle } from '../primitives/CheckboxToggle';
import { FieldError } from '../primitives/FieldError';

interface Props {
  value: TradeManagement;
  onChange: (next: TradeManagement) => void;
  errors: Record<string, string>;
  stepNumber: number;
  totalSteps: number;
}

export function Step14Management({ value, onChange, errors, stepNumber, totalSteps }: Props) {
  const set = <K extends keyof TradeManagement>(key: K, v: TradeManagement[K]) =>
    onChange({ ...value, [key]: v });
  return (
    <StepShell
      stepNumber={stepNumber}
      totalSteps={totalSteps}
      title="Trade Management"
      description="How Exoper manages the trade once it's live — partial closes, trailing, break-even, and runners."
    >
      <div>
        <div className="text-sm font-medium text-content mb-2">Partial take-profit style</div>
        <RadioCardGroup
          name="partial_tp_style"
          value={value.partial_tp_style}
          onChange={(v) => set('partial_tp_style', v)}
          options={[
            { value: 'disabled', label: 'Disabled', description: 'Single TP, no partials' },
            { value: 'aggressive', label: 'Aggressive', description: 'Lock profit early at TP1' },
            { value: 'balanced', label: 'Balanced', description: 'Equal partials at TP1/TP2/TP3' },
            { value: 'let_run', label: 'Let run', description: 'Small first partial, hold runner' },
          ]}
        />
        <FieldError message={errors['management.partial_tp_style']} />
      </div>
      <div>
        <div className="text-sm font-medium text-content mb-2">Trailing stop</div>
        <RadioCardGroup
          name="trailing_stop"
          value={value.trailing_stop}
          onChange={(v) => set('trailing_stop', v)}
          options={[
            { value: 'disabled', label: 'Disabled' },
            { value: 'structure_based', label: 'Structure-based', description: 'Trail behind new swing points' },
            { value: 'atr_based', label: 'ATR-based', description: 'Trail at N×ATR' },
            { value: 'fixed_pips', label: 'Fixed pips', description: 'Trail at a fixed distance' },
          ]}
        />
        <FieldError message={errors['management.trailing_stop']} />
      </div>
      <div>
        <div className="text-sm font-medium text-content mb-2">Break-even trigger</div>
        <RadioCardGroup
          name="break_even_trigger"
          value={value.break_even_trigger}
          onChange={(v) => set('break_even_trigger', v)}
          options={[
            { value: 'disabled', label: 'Disabled' },
            { value: 'at_tp1', label: 'At TP1', description: 'Move SL when TP1 fills' },
            { value: 'at_1rr', label: 'At 1R', description: 'Move SL once price reaches 1R' },
            { value: 'at_midpoint', label: 'At midpoint', description: 'Move SL at zone midpoint' },
          ]}
        />
        <FieldError message={errors['management.break_even_trigger']} />
      </div>
      <CheckboxToggle
        label="Scale-in allowed"
        description="Add to a winning position on continuation."
        checked={value.scale_in_enabled}
        onChange={(v) => set('scale_in_enabled', v)}
      />
      <CheckboxToggle
        label="Scale-out allowed"
        description="Trim the position progressively as it works."
        checked={value.scale_out_enabled}
        onChange={(v) => set('scale_out_enabled', v)}
      />
      <CheckboxToggle
        label="Hold runners"
        description="Leave a small position open beyond TP3 to capture trends."
        checked={value.hold_runners}
        onChange={(v) => set('hold_runners', v)}
      />
      <CheckboxToggle
        label="Close before red-folder news"
        description="Flatten exposure before high-impact economic releases."
        checked={value.close_before_news}
        onChange={(v) => set('close_before_news', v)}
      />
    </StepShell>
  );
}
