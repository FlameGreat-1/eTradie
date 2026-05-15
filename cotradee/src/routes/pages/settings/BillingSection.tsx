import {
  AlertCircle,
  Clock,
  CreditCard,
  Crown,
  ExternalLink,
  Pause,
  RefreshCw,
  ShieldCheck,
  XCircle,
  Zap,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth, isAdmin } from '@/features/auth';
import { useBillingPortal } from '@/features/settings/api/billingPortal';
import UsagePanel from '@/features/settings/components/UsagePanel';

const TIER_DISPLAY: Record<
  string,
  { label: string; color: string; icon: typeof Crown; description: string }
> = {
  free: {
    label: 'Free',
    color: 'text-content-muted',
    icon: AlertCircle,
    description: '1 symbol · 1 analysis/day · No automated execution',
  },
  pro_byok: {
    label: 'Pro BYOK',
    color: 'text-brand',
    icon: Zap,
    description:
      'Unlimited symbols · Unlimited analyses · Automated execution · Bring your own API key',
  },
  pro_managed: {
    label: 'Pro Managed',
    color: 'text-success',
    icon: Crown,
    description:
      'Unlimited symbols · Unlimited analyses · Automated execution · Platform AI included',
  },
};

/**
 * Full status coverage that matches the canonical Status values emitted
 * by the billing service (src/billing/events/normalized.go) plus the
 * legacy 'trialing' value some providers still send. Missing any of
 * these used to silently fall back to the 'Active' badge which was
 * misleading for paused / refunded / unpaid / expired subscriptions.
 */
const STATUS_DISPLAY: Record<string, { label: string; color: string; icon: typeof Clock }> = {
  active:    { label: 'Active',    color: 'text-success', icon: ShieldCheck },
  trialing:  { label: 'Trial',     color: 'text-brand',   icon: Zap },
  past_due:  { label: 'Past Due',  color: 'text-danger',  icon: AlertCircle },
  paused:    { label: 'Paused',    color: 'text-content-muted', icon: Pause },
  canceled:  { label: 'Canceled',  color: 'text-danger',  icon: XCircle },
  refunded:  { label: 'Refunded',  color: 'text-danger',  icon: RefreshCw },
  unpaid:    { label: 'Unpaid',    color: 'text-danger',  icon: AlertCircle },
  expired:   { label: 'Expired',   color: 'text-danger',  icon: Clock },
};

const STATUS_FALLBACK = { label: 'Unknown', color: 'text-content-muted', icon: Clock };

export default function BillingSection() {
  const { user } = useAuth();
  const openPortal = useBillingPortal();

  const tier = user?.tier ?? 'free';
  const status = user?.status ?? 'active';
  const tierInfo = TIER_DISPLAY[tier] ?? TIER_DISPLAY.free;
  const statusInfo = STATUS_DISPLAY[status] ?? STATUS_FALLBACK;
  const TierIcon = tierInfo.icon;
  const StatusIcon = statusInfo.icon;

  const isFree = tier === 'free';
  const admin = isAdmin(user);

  // Admins do not have a subscription record. The backend exempts
  // them from every tier check (see api_handlers.go / router.go).
  // Render an "Unrestricted Access" surface instead of the upgrade
  // funnel + plan-limits comparison that targets free users.
  if (admin) {
    return (
      <div className="space-y-10 max-w-2xl">
        <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <div className="flex flex-col gap-0.5">
              <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Account</div>
              <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Subscription</h3>
            </div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-success/20 bg-success/10 text-success text-[10px] font-black uppercase tracking-widest shadow-sm">
              <ShieldCheck size={12} strokeWidth={3} />
              Admin
            </span>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center justify-center w-16 h-16 rounded-2xl border border-success/20 bg-success/10 shadow-sm">
              <Crown size={32} className="text-success" strokeWidth={2.5} />
            </div>
            <div className="flex flex-col gap-1">
              <p className="text-2xl font-black tracking-tight text-success">Unrestricted Access</p>
              <p className="text-[11px] font-medium text-black/40 dark:text-white/40 leading-relaxed max-w-sm">
                Administrator accounts bypass all subscription gating.
                You have full access to every feature without a paid plan.
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm">
          <p className="text-[11px] font-medium text-black/40 dark:text-white/40 leading-relaxed">
            Platform terms still apply. See our{' '}
            <Link to="/terms" className="font-bold text-black dark:text-white hover:underline underline-offset-4">Terms of Service</Link>{' '}and{' '}
            <Link to="/privacy" className="font-bold text-black dark:text-white hover:underline underline-offset-4">Privacy Policy</Link>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-10 max-w-2xl">
      {/* LLM Token Usage (Pro Managed only; renders nothing for other tiers) */}
      <UsagePanel />

      {/* Current Plan */}
      <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div className="flex flex-col gap-0.5">
            <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Subscription</div>
            <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Current Plan</h3>
          </div>
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[10px] font-black uppercase tracking-widest ${statusInfo.color.replace('text-', 'bg-').replace('text-', 'bg-')}/10 ${statusInfo.color} border-current/20 shadow-sm`}
          >
            <StatusIcon size={12} strokeWidth={3} />
            {statusInfo.label}
          </span>
        </div>

        <div className="flex items-center gap-6 mb-8">
          <div
            className={`flex items-center justify-center w-16 h-16 rounded-2xl border shadow-sm ${
              isFree ? 'bg-black/5 dark:bg-white/5 border-black/10 dark:border-white/10' : 'bg-brand/10 border-brand/20'
            }`}
          >
            <TierIcon size={32} className={tierInfo.color} strokeWidth={2.5} />
          </div>
          <div className="flex flex-col gap-1">
            <p className={`text-2xl font-black tracking-tight ${tierInfo.color}`}>{tierInfo.label}</p>
            <p className="text-[11px] font-medium text-black/40 dark:text-white/40 leading-relaxed max-w-sm">{tierInfo.description}</p>
          </div>
        </div>

        {isFree && (
          <div className="rounded-2xl border border-brand/20 bg-brand/5 p-6 animate-in fade-in slide-in-from-top-2 duration-500">
            <div className="flex items-start gap-4">
              <div className="mt-1 rounded-xl bg-brand/10 p-2 border border-brand/20 shadow-sm">
                <ShieldCheck size={20} className="text-brand" strokeWidth={2.5} />
              </div>
              <div className="flex-1">
                <p className="text-sm font-bold text-black dark:text-white tracking-tight">Unlock Professional Grade Intelligence</p>
                <p className="text-xs font-medium text-black/50 dark:text-white/50 mt-1 leading-relaxed">
                  Upgrade to Pro to unlock unlimited symbols, unlimited analyses, automated trade execution,
                  and institutional-grade guard protection.
                </p>
                <button
                  onClick={() => window.dispatchEvent(new Event('open-upgrade-modal'))}
                  className="mt-5 inline-flex items-center gap-2 rounded-xl bg-black dark:bg-white px-6 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all"
                >
                  <CreditCard size={14} strokeWidth={3} />
                  Upgrade to Pro
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Plan Limits Overview */}
      <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm">
        <div className="flex flex-col gap-0.5 mb-6">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Capabilities</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Plan Limits</h3>
        </div>
        <div className="grid grid-cols-1 gap-1">
          <LimitRow label="Active Symbols" value={isFree ? '1' : 'Unlimited'} isFree={isFree} />
          <LimitRow label="Analyses per Day" value={isFree ? '1' : 'Unlimited'} isFree={isFree} />
          <LimitRow
            label="Automated Execution"
            value={isFree ? 'Blocked' : 'Enabled'}
            isFree={isFree}
          />
          <LimitRow
            label="Automated Scheduling"
            value={isFree ? 'Disabled' : 'Enabled'}
            isFree={isFree}
          />
          <LimitRow
            label="AI Provider"
            value={tier === 'pro_managed' ? 'Platform AI (included)' : 'Bring Your Own Key'}
            isFree={isFree}
          />
        </div>
      </div>

      {/* Subscription Details (only for paying users) */}
      {!isFree && (
        <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm">
          <div className="flex flex-col gap-0.5 mb-6">
            <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Governance</div>
            <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Subscription Details</h3>
          </div>
          <div className="space-y-1">
            <div className="flex items-center justify-between py-3 border-b border-black/5 dark:border-white/5">
              <span className="text-[11px] font-black uppercase tracking-widest text-black/30 dark:text-white/30">Tier</span>
              <span className="text-sm font-bold text-black dark:text-white tracking-tight">{tierInfo.label}</span>
            </div>
            <div className="flex items-center justify-between py-3 border-b border-black/5 dark:border-white/5">
              <span className="text-[11px] font-black uppercase tracking-widest text-black/30 dark:text-white/30">Status</span>
              <span className={`text-sm font-bold tracking-tight ${statusInfo.color}`}>
                {statusInfo.label}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 mt-8">
            <button
              onClick={() => openPortal.mutate()}
              disabled={openPortal.isPending}
              className="inline-flex items-center gap-2 rounded-xl bg-black dark:bg-white px-5 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40"
            >
              <ExternalLink size={14} strokeWidth={3} />
              {openPortal.isPending ? 'Redirecting…' : 'Manage Subscription'}
            </button>
            <button
              onClick={() => window.dispatchEvent(new Event('open-upgrade-modal'))}
              className="inline-flex items-center gap-2 rounded-xl border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 px-5 py-3 text-[10px] font-black uppercase tracking-widest text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white transition-all shadow-sm"
            >
              <CreditCard size={14} strokeWidth={3} />
              Change Plan
            </button>
          </div>
        </div>
      )}

      {/* Always-visible policy strip. Subscribers need one-click
          access to the documents that govern their subscription. */}
      <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm">
        <p className="text-[11px] font-medium text-black/40 dark:text-white/40 leading-relaxed">
          Subscription governed by our{' '}
          <Link to="/billing-policy" className="font-bold text-black dark:text-white hover:underline underline-offset-4">Billing Policy</Link>,{' '}
          <Link to="/refund" className="font-bold text-black dark:text-white hover:underline underline-offset-4">Refund Policy</Link>,{' '}
          <Link to="/terms" className="font-bold text-black dark:text-white hover:underline underline-offset-4">Terms of Service</Link>, and{' '}
          <Link to="/complaints" className="font-bold text-black dark:text-white hover:underline underline-offset-4">Complaints Policy</Link>.
          <span className="block mt-2 opacity-60">Payments are processed by Paddle or Lemon Squeezy, acting as Merchant of Record.</span>
        </p>
      </div>

    </div>
  );
}

function LimitRow({
  label,
  value,
  isFree,
}: {
  label: string;
  value: string;
  isFree: boolean;
}) {
  const isRestricted =
    isFree && (value === '1' || value === 'Blocked' || value === 'Disabled');
  return (
    <div className="flex items-center justify-between py-3 border-b border-black/5 dark:border-white/5 last:border-b-0">
      <span className="text-[11px] font-black uppercase tracking-widest text-black/30 dark:text-white/30">{label}</span>
      <span
        className={`text-sm font-bold tracking-tight ${
          isRestricted ? 'text-red-500' : 'text-green-500'
        }`}
      >
        {value}
      </span>
    </div>
  );
}
