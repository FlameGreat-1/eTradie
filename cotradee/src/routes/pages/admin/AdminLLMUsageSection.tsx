import { useState } from 'react';
import { Activity, AlertTriangle, RefreshCw, Users, Zap } from 'lucide-react';
import {
  useAdminLLMAggregate,
  useAdminLLMUsage,
  type AdminLLMUsageRow,
} from '@/features/admin/api/billing';

const SIZE = 25;

const fmt = (n: number): string => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return String(n);
};

export default function AdminLLMUsageSection() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const agg = useAdminLLMAggregate();
  const list = useAdminLLMUsage(search, page, SIZE);

  const rows = list.data?.rows ?? [];
  const total = list.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / SIZE));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-brand" strokeWidth={2.5} />
          <h2 className="text-base font-bold text-content tracking-tight">
            AI Token Usage
          </h2>
        </div>
        <button
          onClick={() => {
            agg.refetch();
            list.refetch();
          }}
          disabled={agg.isFetching || list.isFetching}
          className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-[11px] font-semibold text-content-muted hover:text-content disabled:opacity-40 transition-colors"
        >
          <RefreshCw size={12} className={agg.isFetching || list.isFetching ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Aggregate tiles */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <Tile label="Input (month)" value={fmt(agg.data?.input_tokens_month ?? 0)} icon={Zap} />
        <Tile label="Output (month)" value={fmt(agg.data?.output_tokens_month ?? 0)} icon={Zap} />
        <Tile label="Input (today)" value={fmt(agg.data?.input_tokens_today ?? 0)} />
        <Tile label="Output (today)" value={fmt(agg.data?.output_tokens_today ?? 0)} />
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
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(1);
        }}
        className="w-full md:max-w-md rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-content placeholder:text-content-muted"
      />

      {/* Per-user table */}
      <div className="rounded-xl border border-border bg-surface-1 overflow-x-auto">
        {list.isLoading ? (
          <div className="p-8 text-center text-sm text-content-muted">Loading…</div>
        ) : list.isError ? (
          <div className="p-8 text-center text-sm text-danger">
            Failed to load user usage. Try refreshing.
          </div>
        ) : rows.length === 0 ? (
          <div className="p-8 text-center text-sm text-content-muted">
            No users match the current search.
          </div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="text-[10px] uppercase tracking-widest text-content-muted bg-surface-2">
              <tr>
                <th className="px-3 py-2 text-left">User</th>
                <th className="px-3 py-2 text-left">Tier</th>
                <th className="px-3 py-2 text-right">Input (month)</th>
                <th className="px-3 py-2 text-right">Output (month)</th>
                <th className="px-3 py-2 text-right">Input (today)</th>
                <th className="px-3 py-2 text-right">Output (today)</th>
                <th className="px-3 py-2 text-right">Blocked (month)</th>
                <th className="px-3 py-2 text-left">Last metered</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <UsageRow key={r.user_id} row={r} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div className="flex items-center justify-between text-xs text-content-muted">
          <span>
            Page {list.data?.page ?? 1} of {totalPages} — {total} users
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded-md border border-border px-3 py-1 disabled:opacity-30"
            >
              Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded-md border border-border px-3 py-1 disabled:opacity-30"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Tile({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  icon?: typeof Zap;
  accent?: 'warn';
}) {
  const accentClass =
    accent === 'warn'
      ? 'border-danger/20 bg-danger/5'
      : 'border-border bg-surface-1';
  return (
    <div className={`rounded-xl border ${accentClass} p-4 shadow-sm`}>
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-content-muted mb-2">
        {Icon && <Icon size={12} />}
        {label}
      </div>
      <p className="text-xl font-bold text-content tracking-tight">{value}</p>
    </div>
  );
}

function UsageRow({ row }: { row: AdminLLMUsageRow }) {
  const lastMetered = row.last_metered_at
    ? new Date(row.last_metered_at).toLocaleString()
    : '—';
  return (
    <tr className="border-t border-border hover:bg-surface-2/40 transition-colors">
      <td className="px-3 py-2">
        <div className="font-semibold text-content">{row.username}</div>
        <div className="text-[11px] text-content-muted">{row.email}</div>
      </td>
      <td className="px-3 py-2 text-content">{row.tier}</td>
      <td className="px-3 py-2 text-right text-content tabular-nums">{fmt(row.input_tokens_month)}</td>
      <td className="px-3 py-2 text-right text-content tabular-nums">{fmt(row.output_tokens_month)}</td>
      <td className="px-3 py-2 text-right text-content-muted tabular-nums">{fmt(row.input_tokens_today)}</td>
      <td className="px-3 py-2 text-right text-content-muted tabular-nums">{fmt(row.output_tokens_today)}</td>
      <td className="px-3 py-2 text-right text-content tabular-nums">{row.blocked_month}</td>
      <td className="px-3 py-2 text-[11px] text-content-muted">{lastMetered}</td>
    </tr>
  );
}
