/**
 * ProviderQuotaModal
 *
 * Globally mounted modal that opens when a BYOK user's OWN provider
 * (Anthropic / OpenAI / Gemini / self-hosted) returns a quota or
 * rate-limit error. The modal listens for the
 * 'open-llm-provider-quota-modal' window CustomEvent fired by
 * cotradee/src/features/realtime/RealtimeProvider.tsx on receipt of
 * an LLM_PROVIDER_QUOTA_EXCEEDED event published by the engine
 * (src/engine/processor/service.py, Step 9).
 *
 * Copy is DELIBERATELY distinct from QuotaExhaustedModal because the
 * cause and the fix are different: the user's OWN provider account
 * is over its limit; the platform did not debit anything. The CTA
 * points at the user's provider dashboard, not at platform support.
 *
 * Audit ref: ADMIN-QUOTA-13.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X, AlertCircle, ExternalLink, KeyRound } from 'lucide-react';

/** Detail payload shape. Matches alert_publisher.publish_llm_provider_quota_exceeded. */
interface ProviderQuotaDetail {
  provider?: string;
  model?: string;
  detail?: string;
  code?: string; // 'quota_exceeded' | 'rate_limited'
}

type IncomingDetail =
  | ProviderQuotaDetail
  | { details?: ProviderQuotaDetail };

function extractDetail(raw: unknown): ProviderQuotaDetail {
  if (!raw || typeof raw !== 'object') return {};
  const r = raw as IncomingDetail;
  if ('details' in r && r.details && typeof r.details === 'object') {
    return r.details;
  }
  return r as ProviderQuotaDetail;
}

interface ProviderInfo {
  label: string;
  dashboardUrl: string | null;
}

/**
 * Provider dashboard deep-link map. Mirrors the four providers the
 * metering layer's policyForUser() recognises. Unknown / self-hosted
 * has no canonical dashboard URL because it is operator-configured;
 * we fall back to the generic 'Check your provider account' label.
 */
function providerInfo(p: string | undefined): ProviderInfo {
  switch ((p || '').toLowerCase()) {
    case 'anthropic':
      return { label: 'Anthropic', dashboardUrl: 'https://console.anthropic.com/' };
    case 'openai':
      return { label: 'OpenAI', dashboardUrl: 'https://platform.openai.com/account/usage' };
    case 'gemini':
      return { label: 'Google Gemini', dashboardUrl: 'https://aistudio.google.com/app/apikey' };
    case 'self_hosted':
      return { label: 'your self-hosted endpoint', dashboardUrl: null };
    default:
      return { label: p || 'your AI provider', dashboardUrl: null };
  }
}

function headlineFor(code: string | undefined, providerLabel: string): string {
  if ((code || '').toLowerCase() === 'rate_limited') {
    return `${providerLabel} rate-limited your request`;
  }
  return `${providerLabel} quota exhausted`;
}

function descriptionFor(code: string | undefined): string {
  if ((code || '').toLowerCase() === 'rate_limited') {
    return (
      'Your provider returned a rate-limit error for this request. ' +
      'Wait a moment and retry, or upgrade your provider plan for ' +
      'higher rate-limit headroom.'
    );
  }
  return (
    'Your provider account is out of quota or credit. Top up your ' +
    'account on the provider dashboard, or switch to a different ' +
    'key on the LLM Connections page.'
  );
}

export default function ProviderQuotaModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [detail, setDetail] = useState<ProviderQuotaDetail>({});

  useEffect(() => {
    const handleOpen = (event: Event) => {
      const ce = event as CustomEvent<unknown>;
      setDetail(extractDetail(ce.detail));
      setIsOpen(true);
      document.body.style.overflow = 'hidden';
    };

    window.addEventListener('open-llm-provider-quota-modal', handleOpen);
    return () => {
      window.removeEventListener('open-llm-provider-quota-modal', handleOpen);
      document.body.style.overflow = 'auto';
    };
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const handleClose = () => {
    setIsOpen(false);
    document.body.style.overflow = 'auto';
  };

  if (!isOpen) return null;

  const info = providerInfo(detail.provider);
  const headline = headlineFor(detail.code, info.label);
  const description = descriptionFor(detail.code);

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-[100] flex items-start justify-center bg-black/95 backdrop-blur-md animate-in fade-in duration-500 px-4 py-8 overflow-y-auto"
    >
      <div className="relative w-full max-w-xl bg-white dark:bg-black border border-black/10 dark:border-white/10 rounded-[2.5rem] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-500 my-auto">
        <div className="absolute -top-32 -right-32 w-80 h-80 bg-brand/5 blur-[120px] rounded-full pointer-events-none" />

        {/* Header */}
        <div className="flex items-center justify-between p-8 border-b border-black/5 dark:border-white/5">
          <div className="flex items-center gap-4">
            <div className="p-2 rounded-xl bg-brand/10 border border-brand/20">
              <AlertCircle size={16} className="text-brand" strokeWidth={3} />
            </div>
            <div className="space-y-0.5">
              <h2 className="text-xl font-black text-black dark:text-white uppercase tracking-tight">
                Your AI Provider Hit a Limit
              </h2>
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">
                {headline}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Close"
            className="text-black/20 dark:text-white/20 hover:text-black dark:hover:text-white transition-all p-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5"
          >
            <X size={20} strokeWidth={3} />
          </button>
        </div>

        {/* Body */}
        <div className="p-8 space-y-6">
          <p className="text-sm font-bold text-black/70 dark:text-white/70 leading-relaxed">
            {description}
          </p>

          {/* Provider + model + raw detail */}
          <div className="grid grid-cols-2 gap-3 rounded-2xl bg-black/[0.03] dark:bg-white/[0.03] p-4 border border-black/5 dark:border-white/5">
            <DetailRow label="Provider" value={info.label} />
            <DetailRow label="Model" value={detail.model || '\u2014'} />
            {detail.detail && (
              <div className="col-span-2">
                <p className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">
                  Provider message
                </p>
                <p className="mt-1 text-xs font-mono text-black/70 dark:text-white/70 break-words">
                  {detail.detail}
                </p>
              </div>
            )}
          </div>

          {/* CTAs */}
          <div className="space-y-3">
            {info.dashboardUrl ? (
              <a
                href={info.dashboardUrl}
                target="_blank"
                rel="noreferrer noopener"
                onClick={handleClose}
                className="flex items-center justify-center gap-2 w-full rounded-2xl bg-black dark:bg-white text-white dark:text-black py-4 text-[10px] font-black uppercase tracking-[0.2em] shadow-xl hover:opacity-90 transition-opacity"
              >
                Open {info.label} Dashboard
                <ExternalLink size={14} strokeWidth={3} />
              </a>
            ) : (
              <div className="flex items-center justify-center gap-2 w-full rounded-2xl bg-black/5 dark:bg-white/5 text-black/40 dark:text-white/40 py-4 text-[10px] font-black uppercase tracking-[0.2em]">
                Check {info.label} for usage
              </div>
            )}
            <Link
              to="/settings/llm-keys"
              onClick={handleClose}
              className="flex items-center justify-center gap-2 w-full rounded-2xl border border-black/10 dark:border-white/10 py-4 text-[10px] font-black uppercase tracking-[0.2em] text-black dark:text-white hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
            >
              <KeyRound size={14} strokeWidth={3} />
              Manage Your Keys
            </Link>
          </div>

          <p className="text-[10px] text-black/30 dark:text-white/30 text-center tracking-wide">
            This limit was set by your provider, not by the platform.
            The platform never debits your account directly.
          </p>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">
        {label}
      </p>
      <p className="mt-1 text-sm font-bold text-black dark:text-white">{value}</p>
    </div>
  );
}
