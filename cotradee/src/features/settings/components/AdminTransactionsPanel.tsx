import { useState } from 'react';
import { ChevronDown, ChevronRight, Receipt, RefreshCw } from 'lucide-react';
import {
  useAdminTransactions,
  useAdminUserTransactions,
  type AdminSubscriptionEventRow,
  type TransactionFilter,
} from '@/features/admin/api/billing';

const PAGE_SIZE = 20;

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

// AdminTransactionsPanel is rendered inline inside PaymentSection when
// isAdmin(user). Regular users never reach this component because the
// parent gates it on the same role check the backend mirrors at
// /api/v1/admin/* (RequireAdmin middleware).
export function AdminTransactionsPanel() {
  const [filter, setFilter] = useState<TransactionFilter>({});
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, isLoading, isError, refetch, isFetching } = useAdminTransactions(
    filter,
    page,
    PAGE_SIZE,
  );

  const rows = data?.rows ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const update = (patch: Partial<TransactionFilter>) => {
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
            <Receipt size={16} className="text-brand" strokeWidth={2.5} />
            Payment Transactions
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

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <select
          value={filter.provider ?? ''}
          onChange={(e) => update({ provider: e.target.value })}
          className="rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black px-3 py-2 text-sm text-black dark:text-white"
        >
          {PROVIDERS.map((p) => (
            <option key={p} value={p}>{p === '' ? 'All providers' : p}</option>
          ))}
        </select>
        <select
          value={filter.event_name ?? ''}
          onChange={(e) => update({ event_name: e.target.value })}
          className="rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black px-3 py-2 text-sm text-black dark:text-white"
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
          className="rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black px-3 py-2 text-sm text-black dark:text-white placeholder:text-black/30 dark:placeholder:text-white/30"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black overflow-x-auto">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-black/40 dark:text-white/40">Loading…</div>
        ) : isError ? (
          <div className="p-8 text-center text-sm text-red-500">
            Failed to load transactions. Try refreshing.
          </div>
        ) : rows.length === 0 ? (
          <div className="p-8 text-center text-sm text-black/40 dark:text-white/40">
            No transactions match the current filters.
          </div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="text-[10px] uppercase tracking-widest text-black/30 dark:text-white/30 bg-black/[0.02] dark:bg-white/[0.02]">
              <tr>
                <th className="px-3 py-2 text-left w-8"></th>
                <th className="px-3 py-2 text-left">When</th>
                <th className="px-3 py-2 text-left">User</th>
                <th className="px-3 py-2 text-left">Provider</th>
                <th className="px-3 py-2 text-left">Event</th>
                <th className="px-3 py-2 text-left">Tier</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Event ID</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <TransactionRow
                  key={row.id}
                  row={row}
                  expanded={expanded === String(row.id)}
                  onToggle={() =>
                    setExpanded(expanded === String(row.id) ? null : String(row.id))
                  }
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div className="flex items-center justify-between text-xs text-black/40 dark:text-white/40">
          <span>
            Page {data?.page ?? 1} of {totalPages} — {total} transactions
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded-md border border-black/10 dark:border-white/10 px-3 py-1 disabled:opacity-30"
            >
              Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded-md border border-black/10 dark:border-white/10 px-3 py-1 disabled:opacity-30"
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
      <tr className="border-t border-black/5 dark:border-white/5 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors">
        <td className="px-3 py-2">
          <button onClick={onToggle} className="text-black/40 dark:text-white/40 hover:text-black dark:hover:text-white">
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        </td>
        <td className="px-3 py-2 text-black/60 dark:text-white/60 whitespace-nowrap">
          {ts.toLocaleString()}
        </td>
        <td className="px-3 py-2">
          <div className="font-semibold text-black dark:text-white">{row.username}</div>
          <div className="text-[11px] text-black/40 dark:text-white/40">{row.email}</div>
        </td>
        <td className="px-3 py-2 text-black/60 dark:text-white/60">{row.provider}</td>
        <td className="px-3 py-2 text-black dark:text-white">{row.event_name}</td>
        <td className="px-3 py-2 text-black dark:text-white">{tierChange}</td>
        <td className="px-3 py-2 text-black dark:text-white">{statusChange}</td>
        <td className="px-3 py-2 text-[11px] text-black/40 dark:text-white/40 font-mono">{row.event_id}</td>
      </tr>
      {expanded && (
        <tr className="bg-black/[0.02] dark:bg-white/[0.02] border-t border-black/5 dark:border-white/5">
          <td colSpan={8} className="px-6 py-3">
            <p className="text-[10px] uppercase tracking-widest text-black/40 dark:text-white/40 mb-2">
              Full history for {row.username}
            </p>
            {userTx.isLoading ? (
              <p className="text-xs text-black/40 dark:text-white/40">Loading…</p>
            ) : userTx.isError ? (
              <p className="text-xs text-red-500">Failed to load user history.</p>
            ) : (
              <ul className="space-y-1 text-[11px]">
                {(userTx.data?.rows ?? []).map((ev) => (
                  <li key={ev.id} className="flex items-center gap-3 text-black/60 dark:text-white/60">
                    <span className="font-mono w-44 shrink-0">
                      {new Date(ev.event_timestamp).toLocaleString()}
                    </span>
                    <span className="font-semibold text-black dark:text-white w-48">{ev.event_name}</span>
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
