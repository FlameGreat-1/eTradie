import { useState } from 'react';
import { Crown, RefreshCw } from 'lucide-react';
import {
  useAdminSubscriptions,
  type AdminSubscriptionRow,
  type SubscriptionFilter,
} from '@/features/admin/api/billing';

const TIERS = ['', 'free', 'pro_byok', 'pro_managed'];
const STATUSES = [
  '', 'active', 'trialing', 'past_due', 'paused',
  'canceled', 'refunded', 'unpaid', 'expired',
];
const PROVIDERS = ['', 'paddle', 'lemonsqueezy'];
const SIZE = 25;

export default function AdminSubscriptionsSection() {
  const [filter, setFilter] = useState<SubscriptionFilter>({});
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, refetch, isFetching } = useAdminSubscriptions(filter, page, SIZE);

  const rows = data?.rows ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / SIZE));

  const update = (patch: Partial<SubscriptionFilter>) => {
    setFilter((f) => ({ ...f, ...patch }));
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Crown size={18} className="text-brand" strokeWidth={2.5} />
          <h2 className="text-base font-bold text-content tracking-tight">
            Subscriptions
          </h2>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-[11px] font-semibold text-content-muted hover:text-content disabled:opacity-40 transition-colors"
        >
          <RefreshCw size={12} className={isFetching ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <select
          value={filter.tier ?? ''}
          onChange={(e) => update({ tier: e.target.value })}
          className="rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-content"
        >
          {TIERS.map((t) => <option key={t} value={t}>{t === '' ? 'All tiers' : t}</option>)}
        </select>
        <select
          value={filter.status ?? ''}
          onChange={(e) => update({ status: e.target.value })}
          className="rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-content"
        >
          {STATUSES.map((s) => <option key={s} value={s}>{s === '' ? 'All statuses' : s}</option>)}
        </select>
        <select
          value={filter.provider ?? ''}
          onChange={(e) => update({ provider: e.target.value })}
          className="rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-content"
        >
          {PROVIDERS.map((p) => <option key={p} value={p}>{p === '' ? 'All providers' : p}</option>)}
        </select>
        <input
          type="text"
          placeholder="Search username/email…"
          value={filter.search ?? ''}
          onChange={(e) => update({ search: e.target.value })}
          className="rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-content placeholder:text-content-muted"
        />
      </div>

      <div className="rounded-xl border border-border bg-surface-1 overflow-x-auto">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-content-muted">Loading…</div>
        ) : isError ? (
          <div className="p-8 text-center text-sm text-danger">
            Failed to load subscriptions. Try refreshing.
          </div>
        ) : rows.length === 0 ? (
          <div className="p-8 text-center text-sm text-content-muted">
            No subscriptions match the current filters.
          </div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="text-[10px] uppercase tracking-widest text-content-muted bg-surface-2">
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
            <tbody>
              {rows.map((r) => <SubRow key={r.user_id} row={r} />)}
            </tbody>
          </table>
        )}
      </div>

      {total > 0 && (
        <div className="flex items-center justify-between text-xs text-content-muted">
          <span>Page {data?.page ?? 1} of {totalPages} — {total} subscriptions</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded-md border border-border px-3 py-1 disabled:opacity-30"
            >Prev</button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded-md border border-border px-3 py-1 disabled:opacity-30"
            >Next</button>
          </div>
        </div>
      )}
    </div>
  );
}

function SubRow({ row }: { row: AdminSubscriptionRow }) {
  return (
    <tr className="border-t border-border hover:bg-surface-2/40 transition-colors">
      <td className="px-3 py-2">
        <div className="font-semibold text-content">{row.username}</div>
        <div className="text-[11px] text-content-muted">{row.email}</div>
      </td>
      <td className="px-3 py-2 text-content">{row.tier}</td>
      <td className="px-3 py-2 text-content">{row.status}</td>
      <td className="px-3 py-2 text-content-muted">{row.payment_provider ?? '—'}</td>
      <td className="px-3 py-2 text-[11px] font-mono text-content-muted">{row.provider_customer_id ?? '—'}</td>
      <td className="px-3 py-2 text-content-muted">
        {row.current_period_end ? new Date(row.current_period_end).toLocaleDateString() : '—'}
      </td>
      <td className="px-3 py-2 text-content-muted">
        {new Date(row.updated_at).toLocaleString()}
      </td>
    </tr>
  );
}
