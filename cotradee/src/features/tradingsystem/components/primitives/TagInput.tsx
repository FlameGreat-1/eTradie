import { memo, useState, type KeyboardEvent } from 'react';

interface Props {
  label: string;
  description?: string;
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  maxItems?: number;
  disabled?: boolean;
}

/**
 * Comma- or Enter-separated tag input. Used by Section 12 for the
 * optional `preferred_pairs` list. Server-side normalisation
 * uppercases, dedupes, trims, and caps at 50; we do the same on the
 * client so the user sees the canonical form immediately.
 */
function TagInputInner({
  label,
  description,
  value,
  onChange,
  placeholder = 'EURUSD, XAUUSD…',
  maxItems = 50,
  disabled = false,
}: Props) {
  const [draft, setDraft] = useState('');

  const commit = (raw: string) => {
    const sym = raw.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
    if (!sym || sym.length > 16) return;
    if (value.includes(sym)) return;
    if (value.length >= maxItems) return;
    onChange([...value, sym]);
  };

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      if (draft.trim()) {
        commit(draft);
        setDraft('');
      }
    } else if (e.key === 'Backspace' && !draft && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  };

  const remove = (idx: number) => {
    onChange(value.filter((_, i) => i !== idx));
  };

  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="text-sm font-medium text-content mb-1">{label}</div>
      {description && (
        <div className="text-xs text-content-muted mb-2">{description}</div>
      )}
      <div className="flex flex-wrap items-center gap-1.5 rounded border border-border bg-app px-2 py-1.5 focus-within:border-brand">
        {value.map((sym, idx) => (
          <span
            key={sym}
            className="inline-flex items-center gap-1 rounded bg-brand/15 px-2 py-0.5 text-xs font-medium text-content"
          >
            {sym}
            <button
              type="button"
              disabled={disabled}
              onClick={() => remove(idx)}
              aria-label={`Remove ${sym}`}
              className="text-content-muted hover:text-content focus-ring rounded"
            >
              ×
            </button>
          </span>
        ))}
        <input
          type="text"
          value={draft}
          disabled={disabled || value.length >= maxItems}
          placeholder={value.length === 0 ? placeholder : ''}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKey}
          onBlur={() => {
            if (draft.trim()) {
              commit(draft);
              setDraft('');
            }
          }}
          className="min-w-[8ch] flex-1 bg-transparent text-sm outline-none placeholder:text-content-muted"
          aria-label={label}
        />
      </div>
    </div>
  );
}

export const TagInput = memo(TagInputInner);
