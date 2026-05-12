import { memo, useState, type FormEvent } from 'react';
import { Loader2, Plus, X } from 'lucide-react';
import {
  CATEGORY_LABELS,
  PRIORITY_LABELS,
  TICKET_CATEGORIES,
  TICKET_PRIORITIES,
  useCreateTicket,
  type NewTicketInput,
  type TicketCategory,
  type TicketPriority,
} from '@/features/support';

/**
 * NewTicketModal opens an inline composition surface inside the
 * Support Centre. It is not a real modal dialog: the dashboard layout
 * never benefits from the focus-trap overhead of a portalled dialog
 * here, and an inline panel keeps the back-button history sane on
 * mobile.
 *
 * Validation mirrors the server caps in src/support/models.go so a
 * client-accepted submission should always be accepted by the
 * server.
 */
function NewTicketModal({
  onCreated,
  onCancel,
}: {
  onCreated: (ticketId: string) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<NewTicketInput>({
    subject: '',
    message: '',
    category: 'general',
    priority: 'normal',
  });
  const [errors, setErrors] = useState<{ subject?: string; message?: string }>({});
  const mutation = useCreateTicket();

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const next: typeof errors = {};
    const subject = form.subject.trim();
    if (subject.length < 3) next.subject = 'Subject must be at least 3 characters.';
    if (subject.length > 200) next.subject = 'Subject is too long (max 200).';
    const message = form.message.trim();
    if (message.length < 5) next.message = 'Message must be at least 5 characters.';
    if (message.length > 8000) next.message = 'Message is too long (max 8000).';
    if (Object.keys(next).length > 0) {
      setErrors(next);
      return;
    }
    try {
      const ticket = await mutation.mutateAsync(form);
      onCreated(ticket.id);
    } catch {
      // useCreateTicket already toasts.
    }
  };

  return (
    <section
      className="flex flex-col h-full rounded-xl border border-border bg-surface-1 overflow-hidden"
      aria-labelledby="new-ticket-heading"
    >
      <header className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Plus size={14} className="text-brand" />
          <h2 id="new-ticket-heading" className="text-sm font-bold text-content">
            Open a new ticket
          </h2>
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center justify-center w-7 h-7 rounded-md
                     text-content-muted hover:text-content hover:bg-surface-2
                     transition-colors duration-fast focus-ring"
          aria-label="Cancel"
        >
          <X size={14} />
        </button>
      </header>

      <form id="new-ticket-form" onSubmit={onSubmit} className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3" noValidate>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FieldSelect
            id="new-ticket-category"
            label="Category"
            value={form.category ?? 'general'}
            onChange={(v) => setForm({ ...form, category: v as TicketCategory })}
            options={TICKET_CATEGORIES.map((c) => ({ value: c, label: CATEGORY_LABELS[c] }))}
          />
          <FieldSelect
            id="new-ticket-priority"
            label="Priority"
            value={form.priority ?? 'normal'}
            onChange={(v) => setForm({ ...form, priority: v as TicketPriority })}
            options={TICKET_PRIORITIES.map((p) => ({ value: p, label: PRIORITY_LABELS[p] }))}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="new-ticket-subject" className="text-xs font-semibold text-content-secondary">
            Subject
          </label>
          <input
            id="new-ticket-subject"
            type="text"
            value={form.subject}
            onChange={(e) => {
              setForm({ ...form, subject: e.target.value });
              if (errors.subject) setErrors({ ...errors, subject: undefined });
            }}
            required
            maxLength={200}
            aria-invalid={errors.subject ? 'true' : 'false'}
            aria-describedby={errors.subject ? 'new-ticket-subject-error' : undefined}
            placeholder="Briefly describe the issue"
            className="h-9 px-3 rounded-md bg-surface-2 border border-border text-xs text-content
                       placeholder:text-content-muted focus-ring outline-none"
          />
          {errors.subject && (
            <p id="new-ticket-subject-error" className="text-[11px] text-red-500">
              {errors.subject}
            </p>
          )}
        </div>

        <div className="flex flex-col gap-1.5 flex-1">
          <label htmlFor="new-ticket-message" className="text-xs font-semibold text-content-secondary">
            Message
          </label>
          <textarea
            id="new-ticket-message"
            value={form.message}
            onChange={(e) => {
              setForm({ ...form, message: e.target.value });
              if (errors.message) setErrors({ ...errors, message: undefined });
            }}
            required
            rows={8}
            maxLength={8000}
            aria-invalid={errors.message ? 'true' : 'false'}
            aria-describedby={errors.message ? 'new-ticket-message-error' : undefined}
            placeholder="What were you trying to do? What happened instead?"
            className="flex-1 px-3 py-2 rounded-md bg-surface-2 border border-border text-xs text-content
                       placeholder:text-content-muted focus-ring outline-none resize-y"
          />
          <div className="flex items-center justify-between">
            {errors.message ? (
              <p id="new-ticket-message-error" className="text-[11px] text-red-500">
                {errors.message}
              </p>
            ) : (
              <span />
            )}
            <span className="text-[10px] text-content-muted tabular-nums">
              {form.message.length}/8000
            </span>
          </div>
        </div>
      </form>

      <footer className="flex items-center justify-end gap-2 px-4 py-3 border-t border-border">
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center justify-center rounded-md px-3 h-8 text-xs font-semibold
                     text-content-muted hover:text-content hover:bg-surface-2
                     transition-colors duration-fast focus-ring"
        >
          Cancel
        </button>
        <button
          type="submit"
          form="new-ticket-form"
          disabled={mutation.isPending}
          className="inline-flex items-center gap-1.5 rounded-md bg-brand px-4 h-8 text-xs font-semibold
                     text-white hover:bg-brand-hover transition-colors duration-fast focus-ring
                     disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {mutation.isPending ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
          {mutation.isPending ? 'Opening…' : 'Open ticket'}
        </button>
      </footer>
    </section>
  );
}

function FieldSelect({
  id,
  label,
  value,
  onChange,
  options,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-xs font-semibold text-content-secondary">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 px-3 rounded-md bg-surface-2 border border-border text-xs text-content
                   focus-ring outline-none"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export default memo(NewTicketModal);
