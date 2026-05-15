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
      className={`flex items-start gap-4 rounded-2xl border p-4 transition-all duration-300
                  ${checked ? 'border-black/40 dark:border-white/40 bg-black/10 dark:bg-white/10 shadow-lg' : 'border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] hover:bg-black/[0.02] dark:hover:bg-white/[0.04]'}
                  ${disabled ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <div className="relative flex items-center mt-0.5">
        <input
          type="checkbox"
          className="h-5 w-5 rounded-lg border-black/20 dark:border-white/20 bg-white dark:bg-black text-brand focus:ring-0 focus:ring-offset-0 cursor-pointer transition-colors checked:border-brand"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
        />
      </div>
      <div className="flex-1">
        <div className={`text-sm font-bold ${checked ? 'text-black dark:text-white' : 'text-black/70 dark:text-white/70'}`}>{label}</div>
        {description && (
          <div className="text-[11px] text-black/40 dark:text-white/40 font-medium leading-relaxed mt-1">{description}</div>
        )}
      </div>
    </label>
  );
}

export const CheckboxToggle = memo(CheckboxToggleInner);
