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
    <div role="group" aria-label={name} className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const active = set.has(opt.value);
        return (
          <button
            key={opt.value}
            type="button"
            aria-pressed={active}
            disabled={disabled}
            onClick={() => toggle(opt.value)}
            className={`rounded-full border px-3 py-1.5 text-sm font-medium transition-colors focus-ring
              ${active
                ? 'border-brand bg-brand/15 text-content'
                : 'border-border bg-surface text-content-secondary hover:text-content hover:border-content-muted'}
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export const MultiSelectChips = memo(MultiSelectChipsInner) as typeof MultiSelectChipsInner;
