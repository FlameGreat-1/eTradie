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
  isAdmin,
}: {
  ticketId: string;
  onClose?: () => void;
  isAdmin?: boolean;
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
        <span className="flex items-center justify-center w-12 h-12 rounded-full bg-danger-soft text-danger mb-4">
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
    <section className="flex flex-col h-full overflow-hidden">
      <header className="flex items-start justify-between gap-4 px-6 py-4 border-b border-border/30">
        <div className="flex flex-wrap items-center gap-3 min-w-0 flex-1">
          <div className="flex items-center gap-3 shrink-0 w-full mb-1 sm:mb-0 sm:w-auto">
            <StatusBadge status={ticket.status} />
            <h1 className="text-sm font-bold text-content truncate flex-1">
              {ticket.subject}
            </h1>
          </div>
          
          <div className="flex items-center justify-between w-full sm:w-auto gap-3">
            <div className="flex items-center gap-2 shrink-0">
              <span className="font-mono text-[10px] text-content-muted opacity-60 mr-1">
                {ticket.public_ref}
              </span>
              <span className="text-[10px] font-medium text-brand px-2 py-0.5 rounded-full bg-brand-soft/10 border border-brand/20 whitespace-nowrap">
                {CATEGORY_LABELS[ticket.category]} · {PRIORITY_LABELS[ticket.priority]}
              </span>
            </div>

            {onClose && (
              <button
                type="button"
                onClick={onClose}
                className="lg:hidden shrink-0 inline-flex items-center justify-center w-8 h-8 rounded-full
                           text-content-muted hover:text-content hover:bg-surface-2
                           transition-colors duration-fast"
              >
                <X size={16} />
              </button>
            )}
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-8">
        {(ticket.messages ?? []).map((m) => (
          <MessageBubble key={m.id} message={m} isAdmin={isAdmin} />
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
          className="flex flex-col gap-3 px-6 py-6 border-t border-border/30"
        >
          <div className="relative group">
            <textarea
              id="reply-body"
              value={replyBody}
              onChange={(e) => setReplyBody(e.target.value)}
              placeholder={isAdmin ? "Type your official response..." : "Type your reply…"}
              rows={2}
              maxLength={8000}
              className="w-full px-4 py-3 rounded-2xl bg-surface-2/50 border border-border/50 text-xs text-content
                         placeholder:text-content-muted/50 focus:border-brand/50 focus:bg-surface-2 transition-all outline-none resize-none"
            />
          </div>
          <div className="flex items-center justify-between gap-4">
            {confirmingClose ? (
              <div className="flex items-center gap-3">
                <span className="text-[10px] font-bold text-danger uppercase tracking-wider">Close Ticket?</span>
                <button
                  type="button"
                  onClick={onConfirmClose}
                  disabled={closeTicket.isPending}
                  className="text-[10px] font-bold text-content hover:text-danger transition-colors"
                >
                  Confirm
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmingClose(false)}
                  className="text-[10px] font-bold text-content-muted hover:text-content transition-colors"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmingClose(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-danger/10 border border-danger/20 px-3 h-8 text-[11px] font-bold
                           text-danger hover:bg-danger/20 transition-all duration-fast uppercase tracking-widest"
              >
                Close Ticket
              </button>
            )}
            <button
              type="submit"
              disabled={reply.isPending || replyBody.trim().length < 5}
              className="inline-flex items-center gap-2 rounded-full bg-brand px-5 h-8 text-[11px] font-bold
                         text-white hover:bg-brand-hover transition-all duration-fast disabled:opacity-30"
            >
              {reply.isPending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
              Send
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

function MessageBubble({ message, isAdmin }: { message: TicketMessage, isAdmin?: boolean }) {
  const isMe = isAdmin ? message.author_kind === 'staff' : message.author_kind === 'user';
  const isOther = isAdmin ? message.author_kind === 'user' : message.author_kind === 'staff';
  const isSystem = message.author_kind === 'system';

  return (
    <div className={`flex flex-col gap-1.5 ${isMe ? 'items-end' : 'items-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-xs leading-relaxed break-words
          ${
            isMe
              ? 'bg-transparent text-content border border-brand'
              : isOther
                ? 'bg-surface-2 text-content border border-border/40'
                : 'text-content-muted italic opacity-60'
          }`}
      >
        {!isMe && (
          <div className="flex items-center gap-1.5 mb-2 text-[10px] font-bold uppercase tracking-wider opacity-70">
            <MessageSquare size={10} aria-hidden />
            {isOther ? (isAdmin ? 'User' : 'Staff Support') : isSystem ? 'System' : ''}
          </div>
        )}
        {message.body}
      </div>
      <time
        className="text-[10px] text-content-muted opacity-40 px-1"
        dateTime={message.created_at}
      >
        {relativeTime(message.created_at)}
      </time>
    </div>
  );
}

export default memo(TicketDetail);
