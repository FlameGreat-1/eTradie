import { memo, useState, type FormEvent } from 'react';
import { Send, CheckCircle2, Loader2 } from 'lucide-react';
import {
  CATEGORY_LABELS,
  PRIORITY_LABELS,
  TICKET_CATEGORIES,
  TICKET_PRIORITIES,
  useSubmitContact,
  type ContactFormInput,
  type TicketCategory,
  type TicketPriority,
} from '@/features/support';

/**
 * Field-level validation. Mirrors the server caps in src/support/models.go
 * so a successful client-side check should always be accepted by the
 * server. The reverse is also true: a server-side rejection of a value
 * we accepted is a bug in this validator.
 */
function validate(input: ContactFormInput): Partial<Record<keyof ContactFormInput, string>> {
  const errors: Partial<Record<keyof ContactFormInput, string>> = {};

  const email = input.email.trim();
  if (!email) {
    errors.email = 'Email is required.';
  } else {
    const at = email.indexOf('@');
    if (at <= 0 || at === email.length - 1 || !email.includes('.', at)) {
      errors.email = 'Please enter a valid email address.';
    }
  }

  if ((input.name?.length ?? 0) > 120) errors.name = 'Name is too long.';

  const subject = input.subject.trim();
  if (subject.length < 3) errors.subject = 'Subject must be at least 3 characters.';
  if (subject.length > 200) errors.subject = 'Subject is too long (max 200).';

  const message = input.message.trim();
  if (message.length < 5) errors.message = 'Message must be at least 5 characters.';
  if (message.length > 8000) errors.message = 'Message is too long (max 8000).';

  return errors;
}

export interface ContactFormProps {
  /** Pre-fill the email field (e.g. from a signed-in profile). */
  defaultEmail?: string;
  /** Pre-fill the display name field. */
  defaultName?: string;
  /** Visual variant. `card` adds a rounded surface; `bare` is unstyled. */
  variant?: 'card' | 'bare';
  /** Hide the email/name pair (use when the caller already knows the user). */
  hideIdentity?: boolean;
  /** Heading rendered above the form when variant=card. */
  heading?: string;
  /** Optional callback invoked after a successful submission. */
  onSubmitted?: (publicRef: string) => void;
}

function ContactForm({
  defaultEmail = '',
  defaultName = '',
  variant = 'card',
  hideIdentity = false,
  heading = 'Send us a message',
  onSubmitted,
}: ContactFormProps) {
  const [form, setForm] = useState<ContactFormInput>({
    email: defaultEmail,
    name: defaultName,
    subject: '',
    message: '',
    category: 'general',
    priority: 'normal',
  });
  const [errors, setErrors] = useState<Partial<Record<keyof ContactFormInput, string>>>({});
  const [submittedRef, setSubmittedRef] = useState<string | null>(null);
  const mutation = useSubmitContact();

  const handleChange = <K extends keyof ContactFormInput>(key: K, value: ContactFormInput[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) {
      setErrors((prev) => ({ ...prev, [key]: undefined }));
    }
  };

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const v = validate(form);
    if (Object.keys(v).length > 0) {
      setErrors(v);
      return;
    }
    try {
      const ticket = await mutation.mutateAsync(form);
      setSubmittedRef(ticket.public_ref);
      onSubmitted?.(ticket.public_ref);
      setForm({
        email: defaultEmail,
        name: defaultName,
        subject: '',
        message: '',
        category: 'general',
        priority: 'normal',
      });
    } catch {
      // useSubmitContact already shows a toast; nothing else to do.
    }
  };

  const shell =
    variant === 'card'
      ? 'rounded-xl border border-border bg-surface-1 p-4 sm:p-6'
      : '';

  if (submittedRef) {
    return (
      <section className={shell} aria-labelledby="contact-success-heading">
        <div className="flex items-start gap-3">
          <span className="flex items-center justify-center w-10 h-10 rounded-full bg-success-soft text-success shrink-0">
            <CheckCircle2 size={20} />
          </span>
          <div className="flex-1">
            <h2 id="contact-success-heading" className="text-sm font-bold text-content mb-1">
              Thanks — we got your message
            </h2>
            <p className="text-xs text-content-muted leading-relaxed mb-3">
              We'll respond as soon as possible. Keep this reference for your records:
            </p>
            <p className="font-mono text-sm font-semibold text-content mb-4">{submittedRef}</p>
            <button
              type="button"
              onClick={() => setSubmittedRef(null)}
              className="text-xs font-semibold text-brand hover:underline"
            >
              Send another message
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className={shell} aria-labelledby={variant === 'card' ? 'contact-heading' : undefined}>
      {variant === 'card' && (
        <h2 id="contact-heading" className="text-sm font-bold text-content mb-4">
          {heading}
        </h2>
      )}
      <form className="grid grid-cols-1 gap-3" onSubmit={onSubmit} noValidate>
        {!hideIdentity && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <FieldText
              id="contact-email"
              label="Email"
              type="email"
              value={form.email}
              onChange={(v) => handleChange('email', v)}
              error={errors.email}
              required
              placeholder="you@example.com"
              autoComplete="email"
            />
            <FieldText
              id="contact-name"
              label="Name (optional)"
              value={form.name ?? ''}
              onChange={(v) => handleChange('name', v)}
              error={errors.name}
              placeholder="Jane Doe"
              autoComplete="name"
            />
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FieldSelect
            id="contact-category"
            label="Category"
            value={form.category ?? 'general'}
            onChange={(v) => handleChange('category', v as TicketCategory)}
            options={TICKET_CATEGORIES.map((c) => ({ value: c, label: CATEGORY_LABELS[c] }))}
          />
          <FieldSelect
            id="contact-priority"
            label="Priority"
            value={form.priority ?? 'normal'}
            onChange={(v) => handleChange('priority', v as TicketPriority)}
            options={TICKET_PRIORITIES.map((p) => ({ value: p, label: PRIORITY_LABELS[p] }))}
          />
        </div>

        <FieldText
          id="contact-subject"
          label="Subject"
          value={form.subject}
          onChange={(v) => handleChange('subject', v)}
          error={errors.subject}
          required
          placeholder="Briefly describe the issue"
          maxLength={200}
        />

        <FieldTextarea
          id="contact-message"
          label="Message"
          value={form.message}
          onChange={(v) => handleChange('message', v)}
          error={errors.message}
          required
          placeholder="What were you trying to do? What happened instead?"
          maxLength={8000}
          rows={6}
        />

        <div className="flex items-center justify-between gap-3 pt-2">
          <p className="text-[11px] text-content-muted">
            By submitting, you agree to be contacted by the Exoper support team at the email above.
          </p>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-4 h-9 text-xs font-semibold
                       text-white hover:bg-brand-hover transition-colors duration-fast focus-ring
                       disabled:opacity-60 disabled:cursor-not-allowed shrink-0"
          >
            {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            {mutation.isPending ? 'Sending…' : 'Send message'}
          </button>
        </div>
      </form>
    </section>
  );
}

function FieldText({
  id,
  label,
  type = 'text',
  value,
  onChange,
  error,
  required,
  placeholder,
  autoComplete,
  maxLength,
}: {
  id: string;
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  required?: boolean;
  placeholder?: string;
  autoComplete?: string;
  maxLength?: number;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-xs font-semibold text-content-secondary">
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        autoComplete={autoComplete}
        maxLength={maxLength}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? `${id}-error` : undefined}
        className="h-9 px-3 rounded-md bg-surface-2 border border-border text-xs text-content
                   placeholder:text-content-muted focus-ring outline-none"
      />
      {error && (
        <p id={`${id}-error`} className="text-[11px] text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

function FieldTextarea({
  id,
  label,
  value,
  onChange,
  error,
  required,
  placeholder,
  rows = 5,
  maxLength,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  required?: boolean;
  placeholder?: string;
  rows?: number;
  maxLength?: number;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-xs font-semibold text-content-secondary">
        {label}
      </label>
      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        rows={rows}
        maxLength={maxLength}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? `${id}-error` : undefined}
        className="px-3 py-2 rounded-md bg-surface-2 border border-border text-xs text-content
                   placeholder:text-content-muted focus-ring outline-none resize-y"
      />
      <div className="flex items-center justify-between">
        {error ? (
          <p id={`${id}-error`} className="text-[11px] text-danger">
            {error}
          </p>
        ) : (
          <span />
        )}
        {maxLength && (
          <span className="text-[10px] text-content-muted tabular-nums">
            {value.length}/{maxLength}
          </span>
        )}
      </div>
    </div>
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

export default memo(ContactForm);
