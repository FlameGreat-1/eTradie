import { memo } from 'react';
import { MessageSquare, Plus, Loader2 } from 'lucide-react';
import {
  CATEGORY_LABELS,
  PRIORITY_LABELS,
  STATUS_LABELS,
  useMyTickets,
  type Ticket,
} from '@/features/support';

/**
 * TicketList renders the caller's tickets, newest-first, with status
 * and priority badges. Selecting a row passes the ticket id back to
 * the parent via onSelect so the same component is reusable in both
 * single-column (mobile) and split-pane (desktop) layouts.
 *
 * The component is intentionally not paginated yet: the server
 * already caps the page at 25, which is enough for the launch
 * milestone. When the backlog grows we'll add a 'Load more' button
 * that bumps the offset.
 */
function TicketList({
  selectedId,
  onSelect,
  onNewTicket,
}: {
  selectedId?: string | null;
  onSelect: (ticketId: string) => void;
  onNewTicket: () => void;
}) {
  const { data, isLoading, isError } = useMyTickets();

  return (
    <section
      className="flex flex-col h-full rounded-xl border border-border bg-surface-1 overflow-hidden"
      aria-label="Your support tickets"
    >
      <header className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <MessageSquare size={14} className="text-brand" />
          <h2 className="text-xs font-bold text-content uppercase tracking-wide">
            Your tickets
          </h2>
        </div>
        <button
          type="button"
          onClick={onNewTicket}
          className="inline-flex items-center gap-1.5 rounded-md bg-brand px-2.5 h-7 text-[11px] font-semibold
                     text-white hover:bg-brand-hover transition-colors duration-fast focus-ring"
        >
          <Plus size={12} />
          New
        </button>
      </header>

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-32 text-content-muted text-xs">
            <Loader2 size={14} className="animate-spin mr-2" /> Loading…
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center h-32 px-4 text-center">
            <p className="text-xs text-red-500 mb-2">Could not load tickets.</p>
            <p className="text-[11px] text-content-muted">Please refresh the page.</p>
          </div>
        ) : !data || data.tickets.length === 0 ? (
          <EmptyState onNewTicket={onNewTicket} />
        ) : (
          <ul className="divide-y divide-border">
            {data.tickets.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  onClick={() => onSelect(t.id)}
                  className={`w-full text-left px-4 py-3 hover:bg-surface-2 transition-colors duration-fast focus-ring
                              ${selectedId === t.id ? 'bg-surface-2' : ''}`}
                >
                  <TicketRow ticket={t} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function EmptyState({ onNewTicket }: { onNewTicket: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-12 text-center">
      <span className="flex items-center justify-center w-12 h-12 rounded-full bg-brand-soft text-brand mb-4">
        <MessageSquare size={20} />
      </span>
      <p className="text-sm font-bold text-content mb-1">No tickets yet</p>
      <p className="text-xs text-content-muted mb-4 max-w-xs">
        When you open a support ticket, you'll find it here along with the full conversation history.
      </p>
      <button
        type="button"
        onClick={onNewTicket}
        className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-4 h-9 text-xs font-semibold
                   text-white hover:bg-brand-hover transition-colors duration-fast focus-ring"
      >
        <Plus size={14} />
        Open a ticket
      </button>
    </div>
  );
}

function TicketRow({ ticket }: { ticket: Ticket }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <StatusBadge status={ticket.status} />
        <span className="font-mono text-[10px] text-content-muted">{ticket.public_ref}</span>
      </div>
      <p className="text-xs font-semibold text-content line-clamp-1">{ticket.subject}</p>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] text-content-muted">
          {CATEGORY_LABELS[ticket.category]} · {PRIORITY_LABELS[ticket.priority]}
        </span>
        <time
          className="text-[10px] text-content-muted shrink-0"
          dateTime={ticket.updated_at}
          title={new Date(ticket.updated_at).toLocaleString()}
        >
          {relativeTime(ticket.updated_at)}
        </time>
      </div>
    </div>
  );
}

export function StatusBadge({ status }: { status: Ticket['status'] }) {
  const cls = STATUS_BADGE_CLASS[status];
  return (
    <span
      className={`inline-flex items-center px-1.5 h-4 rounded text-[10px] font-bold uppercase tracking-wide ${cls}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

const STATUS_BADGE_CLASS: Record<Ticket['status'], string> = {
  open: 'bg-blue-500/15 text-blue-500',
  pending: 'bg-amber-500/15 text-amber-500',
  resolved: 'bg-emerald-500/15 text-emerald-500',
  closed: 'bg-slate-500/15 text-slate-400',
};

export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diff = Date.now() - then;
  const sec = Math.round(diff / 1000);
  if (sec < 30) return 'just now';
  if (sec < 60) return `${sec}s ago`;
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day < 7) return `${day}d ago`;
  const week = Math.round(day / 7);
  if (week < 5) return `${week}w ago`;
  const mo = Math.round(day / 30);
  if (mo < 12) return `${mo}mo ago`;
  const yr = Math.round(day / 365);
  return `${yr}y ago`;
}

export default memo(TicketList);
