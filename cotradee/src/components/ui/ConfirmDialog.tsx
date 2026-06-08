import { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';

interface ConfirmDialogProps {
  /** When false the dialog renders nothing. */
  open: boolean;
  title: string;
  description: string;
  /** Confirm button label. Defaults to "Confirm". */
  confirmLabel?: string;
  /** Cancel button label. Defaults to "Cancel". */
  cancelLabel?: string;
  /** Red confirm button + warning icon when true. */
  danger?: boolean;
  /** Disables the buttons and shows the pending label while true. */
  pending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * A focused, reusable confirmation modal. The caller owns the open
 * state and the confirm action; this component only renders the prompt
 * and routes the two outcomes back. It deliberately does not perform
 * the action itself so it stays generic across every call site.
 */
export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  danger = false,
  pending = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !pending) onCancel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, pending, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => {
          if (!pending) onCancel();
        }}
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-sm rounded-[1.5rem] border border-border bg-white dark:bg-black p-7 shadow-2xl animate-fade-in"
      >
        <div className="flex items-start gap-4">
          {danger && (
            <div className="mt-0.5 rounded-xl bg-danger/10 p-2 border border-danger/20">
              <AlertTriangle size={18} className="text-danger" strokeWidth={2.5} />
            </div>
          )}
          <div className="flex-1">
            <h2 className="text-base font-bold text-content tracking-tight">{title}</h2>
            <p className="mt-1.5 text-[13px] font-medium text-content-secondary leading-relaxed">
              {description}
            </p>
          </div>
        </div>

        <div className="mt-7 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={pending}
            className="rounded-xl border border-border bg-surface-2 px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-content-secondary hover:text-content transition-all disabled:opacity-40"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={pending}
            className={`rounded-xl px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-white transition-all disabled:opacity-40 ${
              danger
                ? 'bg-danger hover:opacity-90 shadow-lg shadow-danger/20'
                : 'bg-black dark:bg-white dark:text-black hover:opacity-90'
            }`}
          >
            {pending ? 'Working\u2026' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
