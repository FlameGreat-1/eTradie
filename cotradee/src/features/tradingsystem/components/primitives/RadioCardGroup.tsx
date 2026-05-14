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
    <div role="radiogroup" aria-label={name} className="grid grid-cols-1 sm:grid-cols-2 gap-2">
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
            className={`text-left rounded-lg border px-3 py-2.5 transition-colors focus-ring
              ${active
                ? 'border-brand bg-brand/10 text-content'
                : 'border-border bg-surface text-content-secondary hover:text-content hover:border-content-muted'}
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <div className="text-sm font-medium">{opt.label}</div>
            {opt.description && (
              <div className="text-xs text-content-muted mt-0.5">{opt.description}</div>
            )}
          </button>
        );
      })}
    </div>
  );
}

export const RadioCardGroup = memo(RadioCardGroupInner) as typeof RadioCardGroupInner;
