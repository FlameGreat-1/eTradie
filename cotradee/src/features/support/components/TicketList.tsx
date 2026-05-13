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
  isAdmin,
}: {
  selectedId?: string | null;
  onSelect: (ticketId: string) => void;
  onNewTicket: () => void;
  isAdmin?: boolean;
}) {
  const { data, isLoading, isError } = useMyTickets();

  return (
    <section
      className="flex flex-col h-full overflow-hidden"
      aria-label="Your support tickets"
    >
      <header className="flex items-center justify-between px-4 py-4">
        <h2 className="text-[11px] font-bold text-content uppercase tracking-widest opacity-60">
          {isAdmin ? 'Inbound' : 'History'}
        </h2>
        {!isAdmin && (
          <button
            type="button"
            onClick={onNewTicket}
            className="group relative flex items-center h-8 w-8 rounded-full border border-brand/40 
                       text-content hover:w-28 hover:bg-brand/10 hover:border-brand transition-all duration-300 overflow-hidden"
          >
            <div className="absolute inset-0 flex items-center justify-center w-8">
              <Plus size={16} strokeWidth={3} />
            </div>
            <div className="ml-8 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap px-2">
              <span className="text-[10px] font-bold">New Ticket</span>
            </div>
          </button>
        )}
      </header>

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-32 text-content-muted text-xs">
            <Loader2 size={14} className="animate-spin mr-2" /> Loading…
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center h-32 px-4 text-center">
            <p className="text-xs text-danger mb-2">Could not load tickets.</p>
            <p className="text-[11px] text-content-muted">Please refresh the page.</p>
          </div>
        ) : !data || data.tickets.length === 0 ? (
          <EmptyState onNewTicket={onNewTicket} />
        ) : (
          <ul className="space-y-1 px-2">
            {data.tickets.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  onClick={() => onSelect(t.id)}
                  className={`w-full text-left px-3 py-3 rounded-lg transition-all duration-fast focus-ring
                              ${selectedId === t.id 
                                ? 'bg-surface-2 text-content' 
                                : 'text-content-muted hover:bg-surface-2/50 hover:text-content'}`}
                >
                  <TicketRow ticket={t} isAdmin={isAdmin} isActive={selectedId === t.id} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function EmptyState({ onNewTicket, isAdmin }: { onNewTicket: () => void, isAdmin?: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-12 text-center">
      <span className="flex items-center justify-center w-12 h-12 rounded-full bg-brand-soft text-brand mb-4">
        <MessageSquare size={20} />
      </span>
      <p className="text-sm font-bold text-content mb-1">
        {isAdmin ? 'Inbox is empty' : 'No tickets yet'}
      </p>
      <p className="text-xs text-content-muted mb-4 max-w-xs">
        {isAdmin
          ? 'There are currently no active support tickets from users.'
          : "When you open a support ticket, you'll find it here along with the full conversation history."}
      </p>
      {!isAdmin && (
        <button
          type="button"
          onClick={onNewTicket}
          className="inline-flex items-center gap-1.5 rounded-lg bg-transparent border border-brand px-4 h-9 text-xs font-semibold
                     text-brand hover:bg-brand/5 transition-colors duration-fast focus-ring"
        >
          <Plus size={14} />
          Open a ticket
        </button>
      )}
    </div>
  );
}

function TicketRow({ ticket, isAdmin, isActive }: { ticket: Ticket, isAdmin?: boolean, isActive?: boolean }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <p className={`text-xs font-semibold truncate ${isActive ? 'text-content' : 'text-content-muted hover:text-content'}`}>
          {ticket.subject}
        </p>
        <time className="text-[10px] text-content-muted opacity-60 shrink-0">
          {relativeTime(ticket.updated_at)}
        </time>
      </div>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 opacity-60">
          <span className="font-mono text-[10px] text-content-muted">{ticket.public_ref}</span>
          <span className="text-[10px] text-content-muted">·</span>
          <span className="text-[10px] text-content-muted truncate">
            {isAdmin ? (ticket.name || ticket.email) : CATEGORY_LABELS[ticket.category]}
          </span>
        </div>
        <span className="text-[9px] font-bold text-brand uppercase tracking-tighter opacity-80">
          {PRIORITY_LABELS[ticket.priority]}
        </span>
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

// Status -> semantic theme tokens. Keeping these aligned with the
// rest of the dashboard means a status badge looks correct in both
// dark and light themes without per-component overrides.
const STATUS_BADGE_CLASS: Record<Ticket['status'], string> = {
  open: 'bg-info-soft text-info',
  pending: 'bg-content/10 text-content',
  resolved: 'bg-success-soft text-success',
  closed: 'bg-content-muted/10 text-content-muted',
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
