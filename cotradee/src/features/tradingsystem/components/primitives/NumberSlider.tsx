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
    <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-5 shadow-sm transition-all duration-300 hover:bg-black/[0.02] dark:hover:bg-white/[0.04]">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div>
          <div className="text-sm font-bold text-black dark:text-white tracking-tight">{label}</div>
          {description && (
            <div className="text-[11px] text-black/40 dark:text-white/40 font-medium leading-relaxed mt-1">{description}</div>
          )}
        </div>
        <div className="flex items-center gap-1 text-sm font-black text-brand tabular-nums bg-brand/10 px-2 py-1 rounded-lg border border-brand/20">
          {value}
          {suffix ?? ''}
        </div>
      </div>
      
      <div className="flex items-center gap-4 mt-4">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(clamp(parseFloat(e.target.value)))}
          className="flex-1 accent-brand h-1.5 rounded-full bg-black/10 dark:bg-white/10 appearance-none cursor-pointer"
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
          className="w-16 rounded-xl border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 px-2 py-2 text-center text-xs font-bold text-black dark:text-white tabular-nums
                     focus:border-brand/40 focus:bg-black/10 dark:focus:bg-white/10 focus:outline-none transition-all"
          aria-label={`${label} numeric`}
        />
      </div>
    </div>
  );
}

export const NumberSlider = memo(NumberSliderInner);
