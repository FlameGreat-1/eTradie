import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle } from 'lucide-react';
import { getLLMUsageSnapshot, type LLMUsageSnapshot } from '../api/usage';

/**
 * UsagePanel renders the Pro Managed LLM token usage for the current
 * billing period. It is only shown when quota_enforced is true (i.e.
 * the user is on the pro_managed tier and the gateway has metering
 * configured). For BYOK users and free users the component renders
 * nothing.
 *
 * The panel polls once on mount. A manual refresh button lets the user
 * re-fetch without reloading the page.
 */
export default function UsagePanel() {
  const [snap, setSnap] = useState<LLMUsageSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const data = await getLLMUsageSnapshot();
    setSnap(data);
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-surface-1 p-6 animate-pulse">
        <div className="h-4 w-32 bg-surface-2 rounded mb-4" />
        <div className="space-y-3">
          <div className="h-3 w-full bg-surface-2 rounded" />
          <div className="h-3 w-3/4 bg-surface-2 rounded" />
        </div>
      </div>
    );
  }

  // Not enforced = free or BYOK tier. Render nothing.
  if (!snap || !snap.quota_enforced) return null;

  const monthlyInputPct =
    snap.monthly_input_limit > 0
      ? Math.min(100, (snap.input_tokens_month / snap.monthly_input_limit) * 100)
      : 0;
  const monthlyOutputPct =
    snap.monthly_output_limit > 0
      ? Math.min(100, (snap.output_tokens_month / snap.monthly_output_limit) * 100)
      : 0;

  const isSoftCapBreached =
    snap.soft_cap_percent > 0 &&
    (monthlyInputPct >= snap.soft_cap_percent ||
      monthlyOutputPct >= snap.soft_cap_percent);

  const isHardCapBreached = monthlyInputPct >= 100 || monthlyOutputPct >= 100;

  const resetDate = new Date(snap.monthly_window_start);
  // Next monthly anniversary
  resetDate.setMonth(resetDate.getMonth() + 1);
  const resetLabel = resetDate.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });

  const fmt = (n: number) =>
    n >= 1_000_000
      ? `${(n / 1_000_000).toFixed(1)}M`
      : n >= 1_000
      ? `${(n / 1_000).toFixed(0)}k`
      : String(n);

  return (
    <div className="rounded-xl border border-border bg-surface-1 p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-brand" />
          <h3 className="text-sm font-semibold text-content">AI Token Usage</h3>
        </div>
        <button
          onClick={load}
          className="text-xs text-content-muted hover:text-content transition-colors"
        >
          Refresh
        </button>
      </div>

      {isHardCapBreached && (
        <div className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger/5 p-3">
          <AlertTriangle size={14} className="text-danger mt-0.5 flex-shrink-0" />
          <p className="text-xs text-danger">
            Monthly token limit reached. Analyses are paused until{' '}
            <span className="font-semibold">{resetLabel}</span>.
          </p>
        </div>
      )}

      {!isHardCapBreached && isSoftCapBreached && (
        <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/5 p-3">
          <AlertTriangle size={14} className="text-warning mt-0.5 flex-shrink-0" />
          <p className="text-xs text-warning">
            Approaching monthly token limit. Resets{' '}
            <span className="font-semibold">{resetLabel}</span>.
          </p>
        </div>
      )}

      {!isHardCapBreached && !isSoftCapBreached && (
        <div className="flex items-start gap-2 rounded-lg border border-success/20 bg-success/5 p-3">
          <CheckCircle size={14} className="text-success mt-0.5 flex-shrink-0" />
          <p className="text-xs text-success">
            Token usage is within limits. Resets{' '}
            <span className="font-semibold">{resetLabel}</span>.
          </p>
        </div>
      )}

      {/* Monthly bars */}
      <div className="space-y-4">
        <UsageBar
          label="Monthly input"
          used={snap.input_tokens_month}
          limit={snap.monthly_input_limit}
          pct={monthlyInputPct}
          softPct={snap.soft_cap_percent}
          fmt={fmt}
        />
        <UsageBar
          label="Monthly output"
          used={snap.output_tokens_month}
          limit={snap.monthly_output_limit}
          pct={monthlyOutputPct}
          softPct={snap.soft_cap_percent}
          fmt={fmt}
        />
      </div>

      {/* Today's counters */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          label="Input today"
          value={fmt(snap.input_tokens_today)}
          limit={fmt(snap.daily_input_limit)}
        />
        <StatCard
          label="Output today"
          value={fmt(snap.output_tokens_today)}
          limit={fmt(snap.daily_output_limit)}
        />
      </div>

      {snap.blocked_month > 0 && (
        <p className="text-[11px] text-content-muted">
          {snap.blocked_month} request
          {snap.blocked_month === 1 ? '' : 's'} blocked this month due to quota.
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function UsageBar({
  label,
  used,
  limit,
  pct,
  softPct,
  fmt,
}: {
  label: string;
  used: number;
  limit: number;
  pct: number;
  softPct: number;
  fmt: (n: number) => string;
}) {
  const barColor =
    pct >= 100
      ? 'bg-danger'
      : pct >= softPct && softPct > 0
      ? 'bg-warning'
      : 'bg-brand';

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-content-muted">{label}</span>
        <span className="text-content font-medium">
          {fmt(used)}
          {limit > 0 && (
            <span className="text-content-muted font-normal"> / {fmt(limit)}</span>
          )}
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-surface-2 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${barColor}`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  limit,
}: {
  label: string;
  value: string;
  limit: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface-2 p-3">
      <p className="text-[10px] text-content-muted uppercase tracking-widest mb-1">
        {label}
      </p>
      <p className="text-sm font-bold text-content">
        {value}
        <span className="text-[10px] font-normal text-content-muted ml-1">/ {limit}</span>
      </p>
    </div>
  );
}
