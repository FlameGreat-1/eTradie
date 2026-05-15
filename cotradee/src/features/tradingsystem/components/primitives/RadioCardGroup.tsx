import { memo } from 'react';

export interface RadioCardOption<T extends string> {
  value: T;
  label: string;
  description?: string;
}

interface Props<T extends string> {
  name: string;
  value: T;
  options: ReadonlyArray<RadioCardOption<T>>;
  onChange: (v: T) => void;
  disabled?: boolean;
}

/**
 * Single-select pill group. Each option is a clickable card with a
 * label and optional description. Used for every "pick one" question
 * in the builder so the visual language stays uniform.
 */
function RadioCardGroupInner<T extends string>({
  name,
  value,
  options,
  onChange,
  disabled = false,
}: Props<T>) {
  return (
    <div role="radiogroup" aria-label={name} className="grid grid-cols-1 gap-2.5">
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(opt.value)}
            className={`text-left rounded-xl border p-4 transition-all duration-200
              ${active
                ? 'border-black/40 dark:border-white/40 bg-black/10 dark:bg-white/10 shadow-lg'
                : 'border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] text-black/50 dark:text-white/50 hover:border-black/20 dark:hover:border-white/20 hover:bg-black/[0.02] dark:hover:bg-white/[0.04]'}
              ${disabled ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className={`text-sm font-bold ${active ? 'text-black dark:text-white' : 'text-black/70 dark:text-white/70'}`}>{opt.label}</div>
                {opt.description && (
                  <div className="text-[11px] text-black/40 dark:text-white/40 font-medium mt-1 leading-relaxed">{opt.description}</div>
                )}
              </div>
              {active && (
                <div className="h-5 w-5 rounded-full bg-brand/20 flex items-center justify-center">
                  <svg className="h-3 w-3 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}

export const RadioCardGroup = memo(RadioCardGroupInner) as typeof RadioCardGroupInner;
