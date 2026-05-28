/**
 * QuotaExhaustedModal
 *
 * Globally mounted modal that opens when a platform-key user
 * (pro_managed or admin) hits one of the LLM token caps the admin
 * configured in tier_quota_policies. The modal listens for the
 * 'open-llm-quota-modal' window CustomEvent fired by:
 *
 *   1. cotradee/src/features/realtime/RealtimeProvider.tsx on receipt
 *      of an LLM_QUOTA_EXCEEDED WebSocket event (auto-cycle path).
 *   2. cotradee/src/lib/axios.ts on receipt of an HTTP 429 with body
 *      error_code === 'llm_quota_exceeded' (manual-cycle path).
 *
 * Both sources dispatch the SAME event name so a single subscription
 * here covers both code paths. The most recent detail payload wins
 * if multiple events arrive while the modal is open.
 *
 * Copy is DELIBERATELY distinct from the generic UpgradeModal because
 * the remediation is different: a Pro Managed user is already paying
 * \u2014 raising the cap is an admin policy decision, not a user upgrade.
 *
 * Audit ref: ADMIN-QUOTA-13.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X, Gauge, Clock, RotateCcw, MessageCircle } from 'lucide-react';

/** Detail payload shape. Matches the Go gateway 429 body verbatim. */
interface LLMQuotaDetail {
  dimension?: string;
  limit?: number;
  used?: number;
  requested?: number;
  resets_at?: string;
  retry_after?: number;
  is_admin?: boolean;
}

/**
 * Two possible detail shapes:
 *   - Direct payload (from axios interceptor): the parsed 429 body.
 *   - Realtime event payload (from WS): the whole RealtimeEvent, which
 *     carries the same fields nested under `details`.
 * We accept both so the listener is source-agnostic.
 */
type IncomingDetail =
  | LLMQuotaDetail
  | { details?: LLMQuotaDetail };

function extractDetail(raw: unknown): LLMQuotaDetail {
  if (!raw || typeof raw !== 'object') return {};
  const r = raw as IncomingDetail;
  if ('details' in r && r.details && typeof r.details === 'object') {
    return r.details;
  }
  return r as LLMQuotaDetail;
}

function labelForDimension(dim?: string): string {
  switch ((dim || '').toLowerCase()) {
    case 'daily_input':
      return 'daily input';
    case 'daily_output':
      return 'daily output';
    case 'monthly_input':
      return 'monthly input';
    case 'monthly_output':
      return 'monthly output';
    case 'per_call_input':
      return 'per-request input';
    default:
      return dim || 'AI tokens';
  }
}

function formatLocalResetTime(iso?: string): string {
  if (!iso) return '';
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return '';
  return new Date(ts).toLocaleString();
}

export default function QuotaExhaustedModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [detail, setDetail] = useState<LLMQuotaDetail>({});

  useEffect(() => {
    const handleOpen = (event: Event) => {
      const ce = event as CustomEvent<unknown>;
      setDetail(extractDetail(ce.detail));
      setIsOpen(true);
      document.body.style.overflow = 'hidden';
    };

    window.addEventListener('open-llm-quota-modal', handleOpen);
    return () => {
      window.removeEventListener('open-llm-quota-modal', handleOpen);
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

  const dimLabel = labelForDimension(detail.dimension);
  const resetLocal = formatLocalResetTime(detail.resets_at);
  const isAdmin = Boolean(detail.is_admin);

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
              <Gauge size={16} className="text-brand" strokeWidth={3} />
            </div>
            <div className="space-y-0.5">
              <h2 className="text-xl font-black text-black dark:text-white uppercase tracking-tight">
                Platform AI Tokens Exhausted
              </h2>
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">
                Platform-managed quota
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
            Your platform-managed AI tokens for the <span className="text-brand">{dimLabel}</span>{' '}
            window are exhausted. Until they reset, the platform key
            cannot be used to run new analyses.
          </p>

          {/* Detail grid */}
          <div className="grid grid-cols-2 gap-3 rounded-2xl bg-black/[0.03] dark:bg-white/[0.03] p-4 border border-black/5 dark:border-white/5">
            <DetailRow label="Limit" value={fmtNum(detail.limit)} />
            <DetailRow label="Used" value={fmtNum(detail.used)} />
            {resetLocal && (
              <div className="col-span-2 flex items-center gap-2 text-[11px] text-black/60 dark:text-white/60">
                <Clock size={12} strokeWidth={3} className="text-brand" />
                <span className="font-bold">Resets:</span>
                <span>{resetLocal}</span>
              </div>
            )}
          </div>

          {/* CTA */}
          {isAdmin ? (
            <Link
              to="/settings"
              onClick={handleClose}
              className="flex items-center justify-center gap-2 w-full rounded-2xl bg-black dark:bg-white text-white dark:text-black py-4 text-[10px] font-black uppercase tracking-[0.2em] shadow-xl hover:opacity-90 transition-opacity"
            >
              <RotateCcw size={14} strokeWidth={3} />
              Edit Quota Policy
            </Link>
          ) : (
            <div className="space-y-3">
              <p className="text-xs font-bold text-black/50 dark:text-white/50 leading-relaxed">
                Your subscription includes a monthly token allowance set
                by the platform administrator. If you need a higher
                cap, please reach out to support.
              </p>
              <Link
                to="/support"
                onClick={handleClose}
                className="flex items-center justify-center gap-2 w-full rounded-2xl bg-black dark:bg-white text-white dark:text-black py-4 text-[10px] font-black uppercase tracking-[0.2em] shadow-xl hover:opacity-90 transition-opacity"
              >
                <MessageCircle size={14} strokeWidth={3} />
                Contact Support
              </Link>
            </div>
          )}

          <p className="text-[10px] text-black/30 dark:text-white/30 text-center tracking-wide">
            You can continue using other dashboard features. Quota is
            applied only to analyses that use the platform AI key.
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

function fmtNum(n: number | undefined): string {
  if (n === undefined || n === null || Number.isNaN(n)) return '\u2014';
  return n.toLocaleString();
}
