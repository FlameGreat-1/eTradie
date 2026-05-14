import { memo } from 'react';

interface Props {
  label: string;
  description?: string;
  value: number; // 0..3
  onChange: (v: number) => void;
  disabled?: boolean;
}

const LEVELS: ReadonlyArray<{ value: number; label: string }> = [
  { value: 0, label: 'Ignore' },
  { value: 1, label: 'Low' },
  { value: 2, label: 'Medium' },
  { value: 3, label: 'High' },
];

/**
 * Compact 0..3 importance picker used for every Section 10
 * (Confluence) field. The LLM receives the integer; the user sees
 * the label.
 */
function WeightSliderInner({ label, description, value, onChange, disabled = false }: Props) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="text-sm font-medium text-content">{label}</div>
        <div className="text-xs text-content-muted">{LEVELS[value]?.label ?? ''}</div>
      </div>
      {description && (
        <div className="text-xs text-content-muted mb-2">{description}</div>
      )}
      <div role="radiogroup" aria-label={label} className="grid grid-cols-4 gap-1.5">
        {LEVELS.map((lv) => {
          const active = lv.value === value;
          return (
            <button
              key={lv.value}
              type="button"
              role="radio"
              aria-checked={active}
              disabled={disabled}
              onClick={() => onChange(lv.value)}
              className={`rounded border px-2 py-1.5 text-xs font-medium transition-colors focus-ring
                ${active
                  ? 'border-brand bg-brand/15 text-content'
                  : 'border-border bg-surface text-content-secondary hover:text-content hover:border-content-muted'}
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              {lv.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export const WeightSlider = memo(WeightSliderInner);
