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
    <div className="rounded-xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-4 transition-all duration-300">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="text-sm font-bold text-black dark:text-white tracking-tight">{label}</div>
        <div className="text-[10px] font-black text-brand uppercase tracking-widest bg-brand/10 px-2 py-0.5 rounded-full">{LEVELS[value]?.label ?? ''}</div>
      </div>
      {description && (
        <div className="text-[11px] text-black/40 dark:text-white/40 font-medium leading-relaxed mb-4">{description}</div>
      )}
      <div role="radiogroup" aria-label={label} className="grid grid-cols-4 gap-2">
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
              className={`rounded-lg border px-2 py-2 text-[10px] font-black uppercase tracking-widest transition-all duration-200
                ${active
                  ? 'border-black/40 dark:border-white/40 bg-black/10 dark:bg-white/10 text-black dark:text-white shadow-sm'
                  : 'border-black/5 dark:border-white/5 bg-black/[0.01] dark:bg-white/[0.02] text-black/30 dark:text-white/30 hover:border-black/10 dark:hover:border-white/10 hover:text-black/60 dark:hover:text-white/60'}
                ${disabled ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'}`}
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
