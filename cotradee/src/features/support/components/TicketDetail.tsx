import { memo, useState, type FormEvent } from 'react';
import { Loader2, Send, X, MessageSquare, Hash, AlertCircle } from 'lucide-react';
import {
  CATEGORY_LABELS,
  PRIORITY_LABELS,
  useCloseTicket,
  useReplyToTicket,
  useTicket,
  type TicketMessage,
} from '@/features/support';
import { StatusBadge, relativeTime } from './TicketList';

/**
 * TicketDetail renders a single ticket's thread with grouped messages,
 * a category / priority strip, an inline reply textarea, and a Close
 * action protected by a confirmation toggle.
 *
 * The reply mutation invalidates the cached thread on success so the
 * new message appears immediately. Closed tickets hide the reply box
 * and show a read-only banner.
 */
function TicketDetail({
  ticketId,
  onClose,
}: {
  ticketId: string;
  onClose?: () => void;
}) {
  const { data: ticket, isLoading, isError } = useTicket(ticketId);
  const reply = useReplyToTicket();
  const closeTicket = useCloseTicket();
  const [replyBody, setReplyBody] = useState('');
  const [confirmingClose, setConfirmingClose] = useState(false);

  if (isLoading) {
    return (
      <section className="flex items-center justify-center h-full rounded-xl border border-border bg-surface-1">
        <Loader2 size={20} className="animate-spin text-content-muted" />
      </section>
    );
  }

  if (isError || !ticket) {
    return (
      <section className="flex flex-col items-center justify-center h-full px-6 py-12 text-center rounded-xl border border-border bg-surface-1">
        <span className="flex items-center justify-center w-12 h-12 rounded-full bg-red-500/12 text-red-500 mb-4">
          <AlertCircle size={20} />
        </span>
        <p className="text-sm font-bold text-content mb-1">Ticket not found</p>
        <p className="text-xs text-content-muted">It may have been removed or you no longer have access.</p>
      </section>
    );
  }

  const isClosed = ticket.status === 'closed';

  const onSubmitReply = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const body = replyBody.trim();
    if (body.length < 5) return;
    try {
      await reply.mutateAsync({ ticketId, input: { message: body } });
      setReplyBody('');
    } catch {
      // useReplyToTicket already toasts on failure.
    }
  };

  const onConfirmClose = async () => {
    try {
      await closeTicket.mutateAsync(ticketId);
      setConfirmingClose(false);
    } catch {
      // useCloseTicket already toasts.
    }
  };

  return (
    <section className="flex flex-col h-full rounded-xl border border-border bg-surface-1 overflow-hidden">
      <header className="flex items-start justify-between gap-3 px-4 py-3 border-b border-border">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusBadge status={ticket.status} />
            <span className="inline-flex items-center gap-1 font-mono text-[10px] text-content-muted">
              <Hash size={10} aria-hidden />
              {ticket.public_ref}
            </span>
          </div>
          <h1 className="text-sm font-bold text-content truncate">{ticket.subject}</h1>
          <p className="text-[11px] text-content-muted mt-1">
            {CATEGORY_LABELS[ticket.category]} · {PRIORITY_LABELS[ticket.priority]} · opened {relativeTime(ticket.created_at)}
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 inline-flex items-center justify-center w-7 h-7 rounded-md
                       text-content-muted hover:text-content hover:bg-surface-2
                       transition-colors duration-fast focus-ring"
            aria-label="Close detail panel"
          >
            <X size={14} />
          </button>
        )}
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {(ticket.messages ?? []).map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
      </div>

      {isClosed ? (
        <div className="px-4 py-3 border-t border-border bg-surface-2/40">
          <p className="text-[11px] text-content-muted">
            This ticket is closed. Open a new ticket if you need further help.
          </p>
        </div>
      ) : (
        <form
          onSubmit={onSubmitReply}
          className="flex flex-col gap-2 px-4 py-3 border-t border-border bg-surface-1"
        >
          <label htmlFor="reply-body" className="sr-only">
            Reply
          </label>
          <textarea
            id="reply-body"
            value={replyBody}
            onChange={(e) => setReplyBody(e.target.value)}
            placeholder="Type your reply…"
            rows={3}
            maxLength={8000}
            className="px-3 py-2 rounded-md bg-surface-2 border border-border text-xs text-content
                       placeholder:text-content-muted focus-ring outline-none resize-y"
          />
          <div className="flex items-center justify-between gap-2">
            {confirmingClose ? (
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-content-muted">Close this ticket?</span>
                <button
                  type="button"
                  onClick={onConfirmClose}
                  disabled={closeTicket.isPending}
                  className="inline-flex items-center gap-1.5 rounded-md bg-red-500/15 text-red-500
                             hover:bg-red-500/25 px-2 h-7 text-[11px] font-semibold
                             transition-colors duration-fast focus-ring
                             disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {closeTicket.isPending ? <Loader2 size={11} className="animate-spin" /> : null}
                  Yes, close
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmingClose(false)}
                  className="text-[11px] text-content-muted hover:text-content focus-ring"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmingClose(true)}
                className="text-[11px] text-content-muted hover:text-red-500 transition-colors duration-fast focus-ring"
              >
                Close ticket
              </button>
            )}
            <button
              type="submit"
              disabled={reply.isPending || replyBody.trim().length < 5}
              className="inline-flex items-center gap-1.5 rounded-md bg-brand px-3 h-7 text-[11px] font-semibold
                         text-white hover:bg-brand-hover transition-colors duration-fast focus-ring
                         disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {reply.isPending ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />}
              {reply.isPending ? 'Sending…' : 'Send reply'}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

function MessageBubble({ message }: { message: TicketMessage }) {
  const isUser = message.author_kind === 'user';
  const isStaff = message.author_kind === 'staff';
  const isSystem = message.author_kind === 'system';
  return (
    <div className={`flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
      <div
        className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap break-words
          ${
            isUser
              ? 'bg-brand text-white'
              : isStaff
                ? 'bg-surface-2 text-content border border-border'
                : 'bg-surface-2/60 text-content-muted border border-border italic'
          }`}
      >
        {!isUser && (
          <div className="flex items-center gap-1 mb-1 text-[10px] font-bold uppercase tracking-wide">
            <MessageSquare size={10} aria-hidden />
            {isStaff ? 'Exoper support' : isSystem ? 'System' : 'You'}
          </div>
        )}
        {message.body}
      </div>
      <time
        className="text-[10px] text-content-muted"
        dateTime={message.created_at}
        title={new Date(message.created_at).toLocaleString()}
      >
        {relativeTime(message.created_at)}
      </time>
    </div>
  );
}

export default memo(TicketDetail);
