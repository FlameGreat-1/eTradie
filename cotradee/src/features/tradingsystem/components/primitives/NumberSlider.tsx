import { memo, useCallback } from 'react';

interface Props {
  label: string;
  description?: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
  onChange: (v: number) => void;
  disabled?: boolean;
}

/**
 * Range + numeric input pair. Clamps to [min, max] on every change so
 * the value passed upstream is always in-range. Used for risk %,
 * drawdown caps, simultaneous trades, RR floor, etc.
 */
function NumberSliderInner({
  label,
  description,
  value,
  min,
  max,
  step = 0.1,
  suffix,
  onChange,
  disabled = false,
}: Props) {
  const clamp = useCallback(
    (raw: number) => {
      if (Number.isNaN(raw)) return min;
      if (raw < min) return min;
      if (raw > max) return max;
      return raw;
    },
    [min, max],
  );

  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="text-sm font-medium text-content">{label}</div>
        <div className="text-sm font-semibold text-brand tabular-nums">
          {value}
          {suffix ?? ''}
        </div>
      </div>
      {description && (
        <div className="text-xs text-content-muted mb-2">{description}</div>
      )}
      <div className="flex items-center gap-3">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(clamp(parseFloat(e.target.value)))}
          className="flex-1 accent-brand focus:!outline-none focus:!ring-0 focus-visible:!outline-none focus-visible:!ring-0"
          aria-label={label}
        />
        <input
          type="number"
          min={min}
          max={max}
          step={step}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(clamp(parseFloat(e.target.value)))}
          className="w-20 rounded border border-border bg-surface px-2 py-1 text-right text-sm tabular-nums
                     focus:border-brand focus:outline-none"
          aria-label={`${label} numeric`}
        />
      </div>
    </div>
  );
}

export const NumberSlider = memo(NumberSliderInner);
