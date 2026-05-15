import { memo, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
// Note: the in-house brand mark for the page hero is loaded from the
// public/ folder via the .brand-icon-help mask utility declared in
// cotradee/src/features/faq/faq.css. We import that stylesheet once
// at the SupportCenter level so the class is available on every
// dashboard surface that mounts SupportCenter without any per-route
// CSS plumbing.
import '@/features/faq/faq.css';
import NewTicketModal from './components/NewTicketModal';
import TicketDetail from './components/TicketDetail';
import TicketList from './components/TicketList';
import { useAuth } from '@/features/auth';

// Mirrors src/support/handler.go isValidIDFormat. A 32-char lowercase
// hex string is the ONLY shape a real ticket id can take; rejecting
// anything else before opening the detail panel avoids a flash of an
// empty 'ticket not found' state for a malformed deep link.
function isValidTicketID(raw: string): boolean {
  if (raw.length !== 32) return false;
  for (const ch of raw) {
    if (!((ch >= '0' && ch <= '9') || (ch >= 'a' && ch <= 'f'))) return false;
  }
  return true;
}

/**
 * SupportCenter is the top-level orchestrator used by the authenticated
 * /dashboard/support route.
 *
 * Layout:
 *   - Desktop (lg+): split-pane with the ticket list on the left and
 *     the detail (or new-ticket form) on the right.
 *   - Mobile: stacked. The list shows by default; selecting a ticket
 *     swaps the panel to the detail view, with a back affordance
 *     surfaced by TicketDetail's onClose handler.
 *
 * Below the ticket area we render the public community-links card
 * because community URLs are useful even when the inbox is empty.
 */
type Panel = { kind: 'empty' } | { kind: 'detail'; ticketId: string } | { kind: 'new' };

function SupportCenter() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [panel, setPanel] = useState<Panel>({ kind: 'empty' });
  const [mobileShowDetail, setMobileShowDetail] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  // Honour deep links from the help widget ('?new=1') and from
  // transactional emails ('?ticket=<32hex>'). Consume the query
  // params on mount, then strip them from the URL via
  // setSearchParams({ replace: true }) so a subsequent refresh does
  // not snap the panel back to the deep-linked one.
  useEffect(() => {
    const wantNew = searchParams.get('new') === '1';
    const rawTicket = searchParams.get('ticket') ?? '';
    if (!wantNew && !rawTicket) return;
    if (wantNew) {
      setPanel({ kind: 'new' });
      setMobileShowDetail(true);
    } else if (isValidTicketID(rawTicket)) {
      setPanel({ kind: 'detail', ticketId: rawTicket });
      setMobileShowDetail(true);
    }
    const next = new URLSearchParams(searchParams);
    next.delete('new');
    next.delete('ticket');
    setSearchParams(next, { replace: true });
  // We only want to react to params on mount or when they actually
  // change; the setters are stable.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const openNew = () => {
    setPanel({ kind: 'new' });
    setMobileShowDetail(true);
  };

  const openTicket = (ticketId: string) => {
    setPanel({ kind: 'detail', ticketId });
    setMobileShowDetail(true);
  };

  const closeDetail = () => {
    setPanel({ kind: 'empty' });
    setMobileShowDetail(false);
  };

  const selectedId = panel.kind === 'detail' ? panel.ticketId : null;

  return (
    <div className="h-full flex flex-col animate-fade-in bg-surface-1">
      <div className="flex-none px-6 py-4 border-b border-border/30">
        <header className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-brand-soft text-brand">
            <span className="brand-icon-help" style={{ width: 20, height: 20 }} aria-hidden />
          </div>
          <div>
            <h1 className="text-lg font-bold text-content">
              {isAdmin ? 'Support Management' : 'Support Centre'}
            </h1>
            <p className="text-xs text-content-muted">
              {isAdmin 
                ? 'Manage inbound user tickets and official platform communication.' 
                : 'Open a ticket, follow the conversation, or join the community.'}
            </p>
          </div>
        </header>
      </div>

      <div className="flex-1 min-h-0">
        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] h-full">
          <div className={`${mobileShowDetail ? 'hidden lg:block' : 'block'} h-full border-r border-border/50 bg-surface-1`}>
            <TicketList
              selectedId={selectedId}
              onSelect={openTicket}
              onNewTicket={openNew}
              isAdmin={isAdmin}
            />
          </div>

          <div className={`${mobileShowDetail ? 'block' : 'hidden lg:block'} h-full bg-surface-1/50`}>
            {panel.kind === 'detail' ? (
              <TicketDetail 
                ticketId={panel.ticketId} 
                onClose={closeDetail} 
                isAdmin={isAdmin} 
              />
            ) : panel.kind === 'new' ? (
              <NewTicketModal
                onCancel={closeDetail}
                onCreated={(ticketId) => {
                  setPanel({ kind: 'detail', ticketId });
                  setMobileShowDetail(true);
                }}
              />
            ) : (
              <EmptyDetail onNewTicket={openNew} isAdmin={isAdmin} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyDetail({ onNewTicket, isAdmin }: { onNewTicket: () => void, isAdmin?: boolean }) {
  return (
    <section className="flex flex-col items-center justify-center h-full rounded-xl border border-border bg-surface-1 px-6 py-12 text-center">
      <span className="flex items-center justify-center w-12 h-12 rounded-full bg-brand-soft text-brand mb-4">
        <span className="brand-icon-help" style={{ width: 20, height: 20 }} aria-hidden />
      </span>
      <p className="text-sm font-bold text-content mb-1">
        {isAdmin ? 'Inbound Management' : 'Select a ticket'}
      </p>
      <p className="text-xs text-content-muted max-w-sm mb-4">
        {isAdmin
          ? 'Select a ticket from the left to review the conversation and respond as staff.'
          : 'Pick an existing ticket from the list to see its conversation, or open a new one to get help from our team.'}
      </p>
      {!isAdmin && (
        <button
          type="button"
          onClick={onNewTicket}
          className="inline-flex items-center gap-1.5 rounded-lg bg-transparent border border-brand px-4 h-9 text-xs font-semibold
                     text-brand hover:bg-brand/5 transition-colors duration-fast focus-ring"
        >
          Open a new ticket
        </button>
      )}
    </section>
  );
}

export default memo(SupportCenter);
