import { useState } from 'react';
import { ChevronDown, ChevronRight, Receipt, RefreshCw } from 'lucide-react';
import {
  useAdminTransactions,
  useAdminUserTransactions,
  type AdminSubscriptionEventRow,
  type TransactionFilter,
} from '@/features/admin/api/billing';

const PROVIDERS = ['', 'paddle', 'lemonsqueezy'];
const EVENT_NAMES = [
  '',
  'SUBSCRIPTION_CREATED',
  'SUBSCRIPTION_UPDATED',
  'SUBSCRIPTION_RENEWED',
  'SUBSCRIPTION_PAUSED',
  'SUBSCRIPTION_RESUMED',
  'SUBSCRIPTION_CANCELED',
  'SUBSCRIPTION_REFUNDED',
  'SUBSCRIPTION_PAST_DUE',
  'PAYMENT_SUCCEEDED',
  'PAYMENT_FAILED',
];
const SIZE = 25;

export default function AdminTransactionsSection() {
  const [filter, setFilter] = useState<TransactionFilter>({});
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, isLoading, isError, refetch, isFetching } = useAdminTransactions(
    filter,
    page,
    SIZE,
  );

  const rows = data?.rows ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / SIZE));

  const update = (patch: Partial<TransactionFilter>) => {
    setFilter((f) => ({ ...f, ...patch }));
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Receipt size={18} className="text-brand" strokeWidth={2.5} />
          <h2 className="text-base font-bold text-content tracking-tight">
            Payment Transactions
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

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <select
          value={filter.provider ?? ''}
          onChange={(e) => update({ provider: e.target.value })}
          className="rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-content"
        >
          {PROVIDERS.map((p) => (
            <option key={p} value={p}>{p === '' ? 'All providers' : p}</option>
          ))}
        </select>
        <select
          value={filter.event_name ?? ''}
          onChange={(e) => update({ event_name: e.target.value })}
          className="rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-content"
        >
          {EVENT_NAMES.map((n) => (
            <option key={n} value={n}>{n === '' ? 'All events' : n}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search username or email…"
          value={filter.search ?? ''}
          onChange={(e) => update({ search: e.target.value })}
          className="rounded-lg border border-border bg-surface-1 px-3 py-2 text-sm text-content placeholder:text-content-muted"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-surface-1 overflow-x-auto">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-content-muted">Loading…</div>
        ) : isError ? (
          <div className="p-8 text-center text-sm text-danger">
            Failed to load transactions. Try refreshing.
          </div>
        ) : rows.length === 0 ? (
          <div className="p-8 text-center text-sm text-content-muted">
            No transactions match the current filters.
          </div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="text-[10px] uppercase tracking-widest text-content-muted bg-surface-2">
              <tr>
                <th className="px-3 py-2 text-left w-8"></th>
                <th className="px-3 py-2 text-left">When</th>
                <th className="px-3 py-2 text-left">User</th>
                <th className="px-3 py-2 text-left">Provider</th>
                <th className="px-3 py-2 text-left">Event</th>
                <th className="px-3 py-2 text-left">Tier</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Provider Event ID</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <TransactionRow
                  key={row.id}
                  row={row}
                  expanded={expanded === row.user_id}
                  onToggle={() => setExpanded(expanded === row.user_id ? null : row.user_id)}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div className="flex items-center justify-between text-xs text-content-muted">
          <span>
            Page {data?.page ?? 1} of {totalPages} — {total} total
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

function TransactionRow({
  row,
  expanded,
  onToggle,
}: {
  row: AdminSubscriptionEventRow;
  expanded: boolean;
  onToggle: () => void;
}) {
  const userTx = useAdminUserTransactions(expanded ? row.user_id : null, 50);

  const ts = new Date(row.event_timestamp);
  const tierChange =
    row.previous_tier && row.previous_tier !== row.new_tier
      ? `${row.previous_tier} → ${row.new_tier}`
      : row.new_tier;
  const statusChange =
    row.previous_status && row.previous_status !== row.new_status
      ? `${row.previous_status} → ${row.new_status}`
      : row.new_status;

  return (
    <>
      <tr className="border-t border-border hover:bg-surface-2/40 transition-colors">
        <td className="px-3 py-2">
          <button onClick={onToggle} className="text-content-muted hover:text-content">
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        </td>
        <td className="px-3 py-2 text-content-muted whitespace-nowrap">
          {ts.toLocaleString()}
        </td>
        <td className="px-3 py-2">
          <div className="font-semibold text-content">{row.username}</div>
          <div className="text-[11px] text-content-muted">{row.email}</div>
        </td>
        <td className="px-3 py-2 text-content-muted">{row.provider}</td>
        <td className="px-3 py-2 text-content">{row.event_name}</td>
        <td className="px-3 py-2 text-content">{tierChange}</td>
        <td className="px-3 py-2 text-content">{statusChange}</td>
        <td className="px-3 py-2 text-[11px] text-content-muted font-mono">{row.event_id}</td>
      </tr>
      {expanded && (
        <tr className="bg-surface-2/30 border-t border-border">
          <td colSpan={8} className="px-6 py-3">
            <p className="text-[10px] uppercase tracking-widest text-content-muted mb-2">
              Full history for {row.username}
            </p>
            {userTx.isLoading ? (
              <p className="text-xs text-content-muted">Loading…</p>
            ) : userTx.isError ? (
              <p className="text-xs text-danger">Failed to load user history.</p>
            ) : (
              <ul className="space-y-1 text-[11px]">
                {(userTx.data?.rows ?? []).map((ev) => (
                  <li key={ev.id} className="flex items-center gap-3 text-content-muted">
                    <span className="font-mono w-44 shrink-0">
                      {new Date(ev.event_timestamp).toLocaleString()}
                    </span>
                    <span className="font-semibold text-content w-48">{ev.event_name}</span>
                    <span>{ev.provider}</span>
                    <span>
                      {ev.previous_tier && ev.previous_tier !== ev.new_tier
                        ? `${ev.previous_tier} → ${ev.new_tier}`
                        : ev.new_tier}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </td>
        </tr>
      )}
    </>
  );
}
