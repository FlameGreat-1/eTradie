import { memo } from 'react';

interface Props {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}

/**
 * Accessible on/off toggle with label + description. Used for every
 * boolean preference in the builder (avoid_news_volatility,
 * require_retest, hold_runners, etc.).
 */
function CheckboxToggleInner({ label, description, checked, onChange, disabled = false }: Props) {
  return (
    <label
      className={`flex items-start gap-3 rounded-lg border border-border bg-surface p-3 transition-colors
                  ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-content-muted'}`}
    >
      <input
        type="checkbox"
        className="mt-0.5 h-4 w-4 rounded border-border text-brand focus:ring-brand cursor-pointer"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <div className="flex-1">
        <div className="text-sm font-medium text-content">{label}</div>
        {description && (
          <div className="text-xs text-content-muted mt-0.5">{description}</div>
        )}
      </div>
    </label>
  );
}

export const CheckboxToggle = memo(CheckboxToggleInner);
