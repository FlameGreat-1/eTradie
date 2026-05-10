import { useAuth } from '@/features/auth';
import { Crown, Zap, ShieldCheck, AlertCircle, ExternalLink } from 'lucide-react';
import UpgradeModal from '@/features/settings/components/UpgradeModal';

const TIER_DISPLAY: Record<string, { label: string; color: string; icon: typeof Crown; description: string }> = {
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
    description: 'Unlimited symbols · Unlimited analyses · Automated execution · Bring your own API key',
  },
  pro_managed: {
    label: 'Pro Managed',
    color: 'text-success',
    icon: Crown,
    description: 'Unlimited symbols · Unlimited analyses · Automated execution · Platform AI included',
  },
};

const STATUS_DISPLAY: Record<string, { label: string; color: string }> = {
  active: { label: 'Active', color: 'text-success' },
  past_due: { label: 'Past Due', color: 'text-warning' },
  canceled: { label: 'Canceled', color: 'text-danger' },
  trialing: { label: 'Trial', color: 'text-brand' },
};

export default function BillingSection() {
  const { user } = useAuth();

  const tier = user?.tier ?? 'free';
  const status = user?.status ?? 'active';
  const tierInfo = TIER_DISPLAY[tier] ?? TIER_DISPLAY.free;
  const statusInfo = STATUS_DISPLAY[status] ?? STATUS_DISPLAY.active;
  const TierIcon = tierInfo.icon;

  const isFree = tier === 'free';

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Current Plan */}
      <div className="rounded-xl border border-border bg-surface-1 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-content">Current Plan</h3>
          <span className={`inline-flex items-center gap-1 text-xs font-semibold ${statusInfo.color}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-current" />
            {statusInfo.label}
          </span>
        </div>

        <div className="flex items-center gap-4 mb-4">
          <div className={`flex items-center justify-center w-12 h-12 rounded-xl ${
            isFree ? 'bg-surface-2' : 'bg-brand/10'
          }`}>
            <TierIcon size={24} className={tierInfo.color} />
          </div>
          <div>
            <p className={`text-lg font-bold ${tierInfo.color}`}>{tierInfo.label}</p>
            <p className="text-xs text-content-muted">{tierInfo.description}</p>
          </div>
        </div>

        {isFree && (
          <div className="rounded-lg border border-brand/20 bg-brand/5 p-4">
            <div className="flex items-start gap-3">
              <ShieldCheck size={18} className="text-brand mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold text-content">Upgrade to Pro</p>
                <p className="text-xs text-content-muted mt-1">
                  Unlock unlimited symbols, unlimited analyses, automated trade execution,
                  and institutional-grade guard protection.
                </p>
                <button
                  onClick={() => window.dispatchEvent(new Event('open-upgrade-modal'))}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-brand px-4 py-2 text-xs
                             font-semibold text-black hover:bg-brand-dark transition-colors"
                >
                  <CreditCard size={14} />
                  Upgrade
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Plan Limits Overview */}
      <div className="rounded-xl border border-border bg-surface-1 p-6">
        <h3 className="text-sm font-semibold text-content mb-4">Plan Limits</h3>
        <div className="space-y-3">
          <LimitRow label="Active Symbols" value={isFree ? '1' : 'Unlimited'} isFree={isFree} />
          <LimitRow label="Analyses per Day" value={isFree ? '1' : 'Unlimited'} isFree={isFree} />
          <LimitRow label="Automated Execution" value={isFree ? 'Blocked' : 'Enabled'} isFree={isFree} />
          <LimitRow label="Automated Scheduling" value={isFree ? 'Disabled' : 'Enabled'} isFree={isFree} />
          <LimitRow
            label="AI Provider"
            value={tier === 'pro_managed' ? 'Platform AI (included)' : 'Bring Your Own Key'}
            isFree={isFree}
          />
        </div>
      </div>

      {/* Subscription Details (only for paying users) */}
      {!isFree && (
        <div className="rounded-xl border border-border bg-surface-1 p-6">
          <h3 className="text-sm font-semibold text-content mb-4">Subscription Details</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between py-2 border-b border-border">
              <span className="text-content-muted">Tier</span>
              <span className="font-medium text-content">{tierInfo.label}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-border">
              <span className="text-content-muted">Status</span>
              <span className={`font-medium ${statusInfo.color}`}>{statusInfo.label}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 mt-4">
            <button
              onClick={() => window.dispatchEvent(new Event('open-upgrade-modal'))}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-3 py-2
                         text-xs font-medium text-content hover:bg-surface-3 transition-colors"
            >
              <ExternalLink size={12} />
              Manage Subscription
            </button>
          </div>
        </div>
      )}

      <UpgradeModal />
    </div>
  );
}

function LimitRow({ label, value, isFree }: { label: string; value: string; isFree: boolean }) {
  const isRestricted = isFree && (value === '1' || value === 'Blocked' || value === 'Disabled');
  return (
    <div className="flex items-center justify-between py-2 border-b border-border last:border-b-0">
      <span className="text-xs text-content-muted">{label}</span>
      <span className={`text-xs font-semibold ${isRestricted ? 'text-warning' : 'text-success'}`}>
        {value}
      </span>
    </div>
  );
}
