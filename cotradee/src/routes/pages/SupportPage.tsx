import { memo } from 'react';
import {
  LifeBuoy,
  BookOpen,
  Activity,
  Mail,
  ExternalLink,
  MessageSquare,
} from 'lucide-react';

function SupportPage() {
  const appVersion = (import.meta.env.VITE_APP_VERSION as string | undefined) ?? '1.0.0';
  const apiBase =
    (import.meta.env.VITE_GATEWAY_URL as string | undefined) ??
    (import.meta.env.VITE_ENGINE_URL as string | undefined) ??
    'unknown';
  const env = (import.meta.env.MODE as string | undefined) ?? 'production';

  return (
    <div className="h-full overflow-auto p-4 sm:p-6 animate-fade-in">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <header className="flex items-center gap-3 mb-6">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-brand-soft text-brand">
            <LifeBuoy size={20} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-content">Support &amp; Help</h1>
            <p className="text-xs text-content-muted">
              Find answers, check service status, or get in touch with our team.
            </p>
          </div>
        </header>

        {/* Quick-help cards */}
        <section className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6" aria-label="Quick help">
          <SupportCard
            href="https://docs.example.com"
            icon={<BookOpen size={18} />}
            title="Documentation"
            description="Guides, API reference, and setup tutorials."
          />
          <SupportCard
            href="https://status.example.com"
            icon={<Activity size={18} />}
            title="System Status"
            description="Live status of broker, engine, and gateway services."
          />
          <SupportCard
            href="mailto:support@example.com"
            icon={<Mail size={18} />}
            title="Email Support"
            description="Reach a human within one business day."
          />
        </section>

        {/* Contact form */}
        <section
          className="rounded-xl border border-border bg-surface-1 p-4 sm:p-6 mb-6"
          aria-labelledby="contact-heading"
        >
          <div className="flex items-center gap-2 mb-4">
            <MessageSquare size={16} className="text-brand" />
            <h2 id="contact-heading" className="text-sm font-bold text-content">
              Send us a message
            </h2>
          </div>
          <form
            className="grid grid-cols-1 gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              const form = e.currentTarget;
              const subject = encodeURIComponent(
                (form.elements.namedItem('subject') as HTMLInputElement)?.value || 'Support request',
              );
              const body = encodeURIComponent(
                (form.elements.namedItem('body') as HTMLTextAreaElement)?.value || '',
              );
              window.location.href = `mailto:support@example.com?subject=${subject}&body=${body}`;
            }}
          >
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-semibold text-content-secondary">Subject</span>
              <input
                type="text"
                name="subject"
                required
                placeholder="Briefly describe the issue"
                className="h-9 px-3 rounded-md bg-surface-2 border border-border text-xs text-content
                           placeholder:text-content-muted focus-ring outline-none"
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-semibold text-content-secondary">Message</span>
              <textarea
                name="body"
                required
                rows={5}
                placeholder="What were you trying to do? What happened instead?"
                className="px-3 py-2 rounded-md bg-surface-2 border border-border text-xs text-content
                           placeholder:text-content-muted focus-ring outline-none resize-y"
              />
            </label>
            <div className="flex justify-end">
              <button
                type="submit"
                className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-4 h-9 text-xs font-semibold
                           text-white hover:bg-brand-hover transition-colors duration-fast focus-ring"
              >
                <Mail size={14} />
                Send message
              </button>
            </div>
          </form>
        </section>

        {/* System info */}
        <section
          className="rounded-xl border border-border bg-surface-1 p-4 sm:p-6"
          aria-labelledby="sysinfo-heading"
        >
          <h2 id="sysinfo-heading" className="text-sm font-bold text-content mb-4">
            System information
          </h2>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <InfoRow label="App version" value={appVersion} />
            <InfoRow label="Environment" value={env} />
            <InfoRow label="API endpoint" value={apiBase} mono />
            <InfoRow label="User agent" value={navigator.userAgent} mono truncate />
          </dl>
          <p className="text-[11px] text-content-muted mt-4">
            Include this information when contacting support — it helps us
            diagnose issues faster.
          </p>
        </section>
      </div>
    </div>
  );
}

function SupportCard({
  href,
  icon,
  title,
  description,
}: {
  href: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  const isExternal = href.startsWith('http');
  return (
    <a
      href={href}
      target={isExternal ? '_blank' : undefined}
      rel={isExternal ? 'noopener noreferrer' : undefined}
      className="group flex flex-col gap-2 rounded-xl border border-border bg-surface-1 p-4
                 hover:border-brand transition-colors duration-fast focus-ring"
    >
      <div className="flex items-center justify-between">
        <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-surface-2 text-brand">
          {icon}
        </span>
        {isExternal && (
          <ExternalLink
            size={12}
            className="text-content-muted group-hover:text-brand transition-colors duration-fast"
          />
        )}
      </div>
      <span className="text-sm font-bold text-content">{title}</span>
      <span className="text-[11px] text-content-muted leading-relaxed">{description}</span>
    </a>
  );
}

function InfoRow({
  label,
  value,
  mono,
  truncate,
}: {
  label: string;
  value: string;
  mono?: boolean;
  truncate?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-[10px] font-semibold uppercase tracking-wide text-content-muted">
        {label}
      </dt>
      <dd
        className={`text-content ${mono ? 'font-mono' : 'font-medium'} ${
          truncate ? 'truncate' : ''
        }`}
        title={truncate ? value : undefined}
      >
        {value}
      </dd>
    </div>
  );
}

export default memo(SupportPage);
