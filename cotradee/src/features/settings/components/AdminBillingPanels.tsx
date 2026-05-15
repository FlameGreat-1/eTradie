import { useState } from 'react';
import { Activity, AlertTriangle, Crown, RefreshCw, Users, Zap } from 'lucide-react';
import {
  useAdminLLMAggregate,
  useAdminLLMUsage,
  useAdminSubscriptions,
  type AdminLLMUsageRow,
  type AdminSubscriptionRow,
  type SubscriptionFilter,
} from '@/features/admin/api/billing';

const PAGE_SIZE = 20;

const fmtTokens = (n: number): string => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return String(n);
};

// ---------------------------------------------------------------------------
// AdminLLMUsagePanel
//
// Headline aggregate tiles + paginated per-user table. Rendered inline
// inside BillingSection when isAdmin(user). Regular users never see this
// component because the parent gates it on isAdmin().
// ---------------------------------------------------------------------------
export function AdminLLMUsagePanel() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const agg = useAdminLLMAggregate();
  const list = useAdminLLMUsage(search, page, PAGE_SIZE);

  const rows = list.data?.rows ?? [];
  const total = list.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-0.5">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">
            Global · Admin view
          </div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight flex items-center gap-2">
            <Activity size={16} className="text-brand" strokeWidth={2.5} />
            AI Token Usage
          </h3>
        </div>
        <button
          onClick={() => { agg.refetch(); list.refetch(); }}
          disabled={agg.isFetching || list.isFetching}
          className="inline-flex items-center gap-2 rounded-lg border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white disabled:opacity-40 transition-colors"
        >
          <RefreshCw size={12} className={agg.isFetching || list.isFetching ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Aggregate tiles */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <Tile label="Input (month)" value={fmtTokens(agg.data?.input_tokens_month ?? 0)} icon={Zap} />
        <Tile label="Output (month)" value={fmtTokens(agg.data?.output_tokens_month ?? 0)} icon={Zap} />
        <Tile label="Input (today)" value={fmtTokens(agg.data?.input_tokens_today ?? 0)} />
        <Tile label="Output (today)" value={fmtTokens(agg.data?.output_tokens_today ?? 0)} />
        <Tile label="Blocked (month)" value={String(agg.data?.blocked_month ?? 0)} accent="warn" />
        <Tile label="Active users" value={String(agg.data?.active_users_month ?? 0)} icon={Users} />
      </div>

      {(agg.data?.held_reservations ?? 0) > 0 && (
        <div className="flex items-start gap-2 rounded-lg border border-brand/30 bg-brand/5 p-3">
          <AlertTriangle size={14} className="text-brand mt-0.5 flex-shrink-0" />
          <p className="text-xs text-brand">
            {agg.data?.held_reservations} held reservation
            {agg.data?.held_reservations === 1 ? '' : 's'} pending settlement. The metering
            janitor reaps stale reservations every minute; a persistent non-zero count
            indicates the engine is failing to commit/refund.
          </p>
        </div>
      )}

      {/* Search */}
      <input
        type="text"
        placeholder="Search by username or email…"
        value={search}
        onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        className="w-full md:max-w-md rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black px-3 py-2 text-sm text-black dark:text-white placeholder:text-black/30 dark:placeholder:text-white/30"
      />

      {/* Per-user table */}
      <div className="rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black overflow-x-auto">
        {list.isLoading ? (
          <div className="p-8 text-center text-sm text-black/40 dark:text-white/40">Loading…</div>
        ) : list.isError ? (
          <div className="p-8 text-center text-sm text-red-500">Failed to load user usage. Try refreshing.</div>
        ) : rows.length === 0 ? (
          <div className="p-8 text-center text-sm text-black/40 dark:text-white/40">No users match the current search.</div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="text-[10px] uppercase tracking-widest text-black/30 dark:text-white/30 bg-black/[0.02] dark:bg-white/[0.02]">
              <tr>
                <th className="px-3 py-2 text-left">User</th>
                <th className="px-3 py-2 text-left">Tier</th>
                <th className="px-3 py-2 text-right">In (month)</th>
                <th className="px-3 py-2 text-right">Out (month)</th>
                <th className="px-3 py-2 text-right">In (today)</th>
                <th className="px-3 py-2 text-right">Out (today)</th>
                <th className="px-3 py-2 text-right">Blocked</th>
                <th className="px-3 py-2 text-left">Last metered</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => <UsageRow key={r.user_id} row={r} />)}
            </tbody>
          </table>
        )}
      </div>

      {total > 0 && (
        <div className="flex items-center justify-between text-xs text-black/40 dark:text-white/40">
          <span>Page {list.data?.page ?? 1} of {totalPages} — {total} users</span>
          <Pager page={page} totalPages={totalPages} onChange={setPage} />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// AdminSubscriptionsPanel
// ---------------------------------------------------------------------------
const TIERS = ['', 'free', 'pro_byok', 'pro_managed'];
const STATUSES = ['', 'active', 'trialing', 'past_due', 'paused', 'canceled', 'refunded', 'unpaid', 'expired'];
const PROVIDERS = ['', 'paddle', 'lemonsqueezy'];

export function AdminSubscriptionsPanel() {
  const [filter, setFilter] = useState<SubscriptionFilter>({});
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, refetch, isFetching } = useAdminSubscriptions(filter, page, PAGE_SIZE);

  const rows = data?.rows ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const update = (patch: Partial<SubscriptionFilter>) => {
    setFilter((f) => ({ ...f, ...patch }));
    setPage(1);
  };

  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 shadow-sm space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-0.5">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">
            Global · Admin view
          </div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight flex items-center gap-2">
            <Crown size={16} className="text-brand" strokeWidth={2.5} />
            Subscriptions
          </h3>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-2 rounded-lg border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest text-black/60 dark:text-white/60 hover:text-black dark:hover:text-white disabled:opacity-40 transition-colors"
        >
          <RefreshCw size={12} className={isFetching ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <select value={filter.tier ?? ''} onChange={(e) => update({ tier: e.target.value })} className="rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black px-3 py-2 text-sm text-black dark:text-white">
          {TIERS.map((t) => <option key={t} value={t}>{t === '' ? 'All tiers' : t}</option>)}
        </select>
        <select value={filter.status ?? ''} onChange={(e) => update({ status: e.target.value })} className="rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black px-3 py-2 text-sm text-black dark:text-white">
          {STATUSES.map((s) => <option key={s} value={s}>{s === '' ? 'All statuses' : s}</option>)}
        </select>
        <select value={filter.provider ?? ''} onChange={(e) => update({ provider: e.target.value })} className="rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black px-3 py-2 text-sm text-black dark:text-white">
          {PROVIDERS.map((p) => <option key={p} value={p}>{p === '' ? 'All providers' : p}</option>)}
        </select>
        <input type="text" placeholder="Search username/email…" value={filter.search ?? ''} onChange={(e) => update({ search: e.target.value })} className="rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black px-3 py-2 text-sm text-black dark:text-white placeholder:text-black/30 dark:placeholder:text-white/30" />
      </div>

      <div className="rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black overflow-x-auto">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-black/40 dark:text-white/40">Loading…</div>
        ) : isError ? (
          <div className="p-8 text-center text-sm text-red-500">Failed to load subscriptions. Try refreshing.</div>
        ) : rows.length === 0 ? (
          <div className="p-8 text-center text-sm text-black/40 dark:text-white/40">No subscriptions match the current filters.</div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="text-[10px] uppercase tracking-widest text-black/30 dark:text-white/30 bg-black/[0.02] dark:bg-white/[0.02]">
              <tr>
                <th className="px-3 py-2 text-left">User</th>
                <th className="px-3 py-2 text-left">Tier</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Provider</th>
                <th className="px-3 py-2 text-left">Customer ID</th>
                <th className="px-3 py-2 text-left">Period End</th>
                <th className="px-3 py-2 text-left">Updated</th>
              </tr>
            </thead>
            <tbody>{rows.map((r) => <SubRow key={r.user_id} row={r} />)}</tbody>
          </table>
        )}
      </div>

      {total > 0 && (
        <div className="flex items-center justify-between text-xs text-black/40 dark:text-white/40">
          <span>Page {data?.page ?? 1} of {totalPages} — {total} subscriptions</span>
          <Pager page={page} totalPages={totalPages} onChange={setPage} />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared sub-components
// ---------------------------------------------------------------------------
function Tile({ label, value, icon: Icon, accent }: { label: string; value: string; icon?: typeof Zap; accent?: 'warn' }) {
  const accentClass = accent === 'warn'
    ? 'border-red-500/20 bg-red-500/5'
    : 'border-black/10 dark:border-white/10 bg-white dark:bg-black';
  return (
    <div className={`rounded-xl border ${accentClass} p-4 shadow-sm`}>
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-black/30 dark:text-white/30 mb-2">
        {Icon && <Icon size={12} />}
        {label}
      </div>
      <p className="text-xl font-bold text-black dark:text-white tracking-tight">{value}</p>
    </div>
  );
}

function UsageRow({ row }: { row: AdminLLMUsageRow }) {
  const lastMetered = row.last_metered_at ? new Date(row.last_metered_at).toLocaleString() : '—';
  return (
    <tr className="border-t border-black/5 dark:border-white/5 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors">
      <td className="px-3 py-2">
        <div className="font-semibold text-black dark:text-white">{row.username}</div>
        <div className="text-[11px] text-black/40 dark:text-white/40">{row.email}</div>
      </td>
      <td className="px-3 py-2 text-black dark:text-white">{row.tier}</td>
      <td className="px-3 py-2 text-right text-black dark:text-white tabular-nums">{fmtTokens(row.input_tokens_month)}</td>
      <td className="px-3 py-2 text-right text-black dark:text-white tabular-nums">{fmtTokens(row.output_tokens_month)}</td>
      <td className="px-3 py-2 text-right text-black/60 dark:text-white/60 tabular-nums">{fmtTokens(row.input_tokens_today)}</td>
      <td className="px-3 py-2 text-right text-black/60 dark:text-white/60 tabular-nums">{fmtTokens(row.output_tokens_today)}</td>
      <td className="px-3 py-2 text-right text-black dark:text-white tabular-nums">{row.blocked_month}</td>
      <td className="px-3 py-2 text-[11px] text-black/40 dark:text-white/40">{lastMetered}</td>
    </tr>
  );
}

function SubRow({ row }: { row: AdminSubscriptionRow }) {
  return (
    <tr className="border-t border-black/5 dark:border-white/5 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors">
      <td className="px-3 py-2">
        <div className="font-semibold text-black dark:text-white">{row.username}</div>
        <div className="text-[11px] text-black/40 dark:text-white/40">{row.email}</div>
      </td>
      <td className="px-3 py-2 text-black dark:text-white">{row.tier}</td>
      <td className="px-3 py-2 text-black dark:text-white">{row.status}</td>
      <td className="px-3 py-2 text-black/60 dark:text-white/60">{row.payment_provider ?? '—'}</td>
      <td className="px-3 py-2 text-[11px] font-mono text-black/40 dark:text-white/40">{row.provider_customer_id ?? '—'}</td>
      <td className="px-3 py-2 text-black/60 dark:text-white/60">
        {row.current_period_end ? new Date(row.current_period_end).toLocaleDateString() : '—'}
      </td>
      <td className="px-3 py-2 text-black/60 dark:text-white/60">{new Date(row.updated_at).toLocaleString()}</td>
    </tr>
  );
}

function Pager({ page, totalPages, onChange }: { page: number; totalPages: number; onChange: (n: number) => void }) {
  return (
    <div className="flex items-center gap-2">
      <button onClick={() => onChange(Math.max(1, page - 1))} disabled={page <= 1} className="rounded-md border border-black/10 dark:border-white/10 px-3 py-1 disabled:opacity-30">Prev</button>
      <button onClick={() => onChange(Math.min(totalPages, page + 1))} disabled={page >= totalPages} className="rounded-md border border-black/10 dark:border-white/10 px-3 py-1 disabled:opacity-30">Next</button>
    </div>
  );
}
