import { memo } from 'react';

export interface ChipOption<T extends string> {
  value: T;
  label: string;
}

interface Props<T extends string> {
  name: string;
  value: T[];
  options: ReadonlyArray<ChipOption<T>>;
  onChange: (next: T[]) => void;
  minCount?: number; // 0 = any, 1 = at least one
  disabled?: boolean;
}

/**
 * Multi-select pill row. Enforces minCount client-side by refusing
 * the toggle-off that would drop below it (the server still validates,
 * this is purely UX).
 */
function MultiSelectChipsInner<T extends string>({
  name,
  value,
  options,
  onChange,
  minCount = 0,
  disabled = false,
}: Props<T>) {
  const set = new Set(value);

  const toggle = (v: T) => {
    if (disabled) return;
    if (set.has(v)) {
      if (set.size <= minCount) return;
      set.delete(v);
    } else {
      set.add(v);
    }
    onChange(options.filter((o) => set.has(o.value)).map((o) => o.value));
  };

  return (
    <div role="group" aria-label={name} className="flex flex-wrap gap-2.5">
      {options.map((opt) => {
        const active = set.has(opt.value);
        return (
          <button
            key={opt.value}
            type="button"
            aria-pressed={active}
            disabled={disabled}
            onClick={() => toggle(opt.value)}
            className={`rounded-xl border px-5 py-2.5 text-xs font-bold transition-all duration-200
              ${active
                ? 'border-black/40 dark:border-white/40 bg-black/10 dark:bg-white/10 text-black dark:text-white'
                : 'border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] text-black/40 dark:text-white/40 hover:border-black/20 dark:hover:border-white/20 hover:text-black/60 dark:hover:text-white/60'}
              ${disabled ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export const MultiSelectChips = memo(MultiSelectChipsInner) as typeof MultiSelectChipsInner;
