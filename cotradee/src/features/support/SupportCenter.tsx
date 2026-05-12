import { memo, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { LifeBuoy } from 'lucide-react';
import CommunityLinks from './components/CommunityLinks';
import NewTicketModal from './components/NewTicketModal';
import TicketDetail from './components/TicketDetail';
import TicketList from './components/TicketList';

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
    <div className="h-full overflow-auto p-4 sm:p-6 animate-fade-in">
      <div className="max-w-6xl mx-auto flex flex-col gap-4">
        <header className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-brand-soft text-brand">
            <LifeBuoy size={20} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-content">Support Centre</h1>
            <p className="text-xs text-content-muted">
              Open a ticket, follow the conversation, or join the community.
            </p>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)] gap-4 lg:h-[70vh]">
          <div className={`${mobileShowDetail ? 'hidden lg:block' : 'block'} lg:h-full min-h-[420px]`}>
            <TicketList
              selectedId={selectedId}
              onSelect={openTicket}
              onNewTicket={openNew}
            />
          </div>

          <div className={`${mobileShowDetail ? 'block' : 'hidden lg:block'} lg:h-full min-h-[420px]`}>
            {panel.kind === 'detail' ? (
              <TicketDetail ticketId={panel.ticketId} onClose={closeDetail} />
            ) : panel.kind === 'new' ? (
              <NewTicketModal
                onCancel={closeDetail}
                onCreated={(ticketId) => {
                  setPanel({ kind: 'detail', ticketId });
                  setMobileShowDetail(true);
                }}
              />
            ) : (
              <EmptyDetail onNewTicket={openNew} />
            )}
          </div>
        </div>

        <CommunityLinks />
      </div>
    </div>
  );
}

function EmptyDetail({ onNewTicket }: { onNewTicket: () => void }) {
  return (
    <section className="flex flex-col items-center justify-center h-full rounded-xl border border-border bg-surface-1 px-6 py-12 text-center">
      <span className="flex items-center justify-center w-12 h-12 rounded-full bg-brand-soft text-brand mb-4">
        <LifeBuoy size={20} />
      </span>
      <p className="text-sm font-bold text-content mb-1">Select a ticket</p>
      <p className="text-xs text-content-muted max-w-sm mb-4">
        Pick an existing ticket from the list to see its conversation, or open a new one to get help from our team.
      </p>
      <button
        type="button"
        onClick={onNewTicket}
        className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-4 h-9 text-xs font-semibold
                   text-white hover:bg-brand-hover transition-colors duration-fast focus-ring"
      >
        Open a new ticket
      </button>
    </section>
  );
}

export default memo(SupportCenter);
