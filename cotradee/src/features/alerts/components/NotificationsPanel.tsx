import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { Bell, Inbox, AlertTriangle, AlertCircle, CheckCircle2, Info } from 'lucide-react';
import { useRecentEvents } from '@/features/alerts/api/events';
import { formatRelativeTime } from '@/utils/formatters';

const LAST_SEEN_KEY = 'notifications_last_seen_id';

interface EventLike {
  event_id?: string | number;
  id?: string | number;
  type?: string;
  severity?: string;
  message?: string;
  title?: string;
  symbol?: string;
  created_at?: string;
  timestamp?: string;
}

function getEventId(e: EventLike): string {
  return String(e.event_id ?? e.id ?? '');
}

function getEventTime(e: EventLike): string | undefined {
  return e.created_at ?? e.timestamp;
}

function getEventTitle(e: EventLike): string {
  return e.title ?? e.type ?? 'Event';
}

function severityIcon(sev?: string) {
  switch ((sev ?? '').toLowerCase()) {
    case 'critical':
    case 'error':
      return <AlertCircle size={14} className="text-danger" />;
    case 'warning':
      return <AlertTriangle size={14} className="text-warning" />;
    case 'success':
      return <CheckCircle2 size={14} className="text-success" />;
    default:
      return <Info size={14} className="text-info" />;
  }
}

function severityDotClass(sev?: string): string {
  switch ((sev ?? '').toLowerCase()) {
    case 'critical':
    case 'error':
      return 'bg-danger';
    case 'warning':
      return 'bg-warning';
    case 'success':
      return 'bg-success';
    default:
      return 'bg-info';
  }
}

function NotificationsPanelInner() {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const [lastSeenId, setLastSeenId] = useState<string>(
    () => localStorage.getItem(LAST_SEEN_KEY) ?? '',
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const portalRef = useRef<HTMLDivElement>(null);

  const toggle = () => {
    if (!isOpen && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setCoords({ 
        top: rect.bottom, 
        left: rect.left + rect.width / 2 
      });
    }
    setIsOpen(!isOpen);
  };

  const { data: events, isLoading, isError } = useRecentEvents(20);

  const eventList: EventLike[] = useMemo(() => {
    if (!Array.isArray(events)) return [];
    return [...(events as EventLike[])].sort((a, b) => {
      const timeA = new Date(a.created_at ?? a.timestamp ?? 0).getTime();
      const timeB = new Date(b.created_at ?? b.timestamp ?? 0).getTime();
      return timeB - timeA;
    });
  }, [events]);

  const unreadCount = useMemo(() => {
    if (!eventList.length) return 0;
    if (!lastSeenId) return eventList.length;
    let count = 0;
    for (const e of eventList) {
      if (getEventId(e) === lastSeenId) break;
      count += 1;
    }
    return count;
  }, [eventList, lastSeenId]);

  const close = useCallback(() => setIsOpen(false), []);

  // Click-outside.
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      const clickedOutsideTrigger = containerRef.current && !containerRef.current.contains(target);
      const clickedOutsidePortal = portalRef.current && !portalRef.current.contains(target);

      if (clickedOutsideTrigger && clickedOutsidePortal) {
        close();
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen, close]);

  // Escape-to-close.
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isOpen, close]);

  // When the user opens the panel, record the newest event id as
  // "last seen" so the unread badge clears.
  useEffect(() => {
    if (!isOpen || eventList.length === 0) return;
    const newestId = getEventId(eventList[0]);
    if (!newestId || newestId === lastSeenId) return;
    localStorage.setItem(LAST_SEEN_KEY, newestId);
    setLastSeenId(newestId);
  }, [isOpen, eventList, lastSeenId]);

  const markAllAsRead = useCallback(() => {
    if (eventList.length === 0) return;
    const newestId = getEventId(eventList[0]);
    if (!newestId) return;
    localStorage.setItem(LAST_SEEN_KEY, newestId);
    setLastSeenId(newestId);
  }, [eventList]);

  const goToJournal = useCallback(() => {
    close();
    navigate('/dashboard/journal');
  }, [close, navigate]);

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        title="Notifications"
        aria-label="Notifications"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        onClick={toggle}
        className="relative flex items-center justify-center w-9 h-9 rounded-full
                   bg-surface-2 border border-border hover:border-brand transition-colors duration-fast
                   focus-ring"
      >
        <img src="/assets/dashboard/icons/bellIcon.svg" alt="Notifications" className="w-[18px] h-[18px] object-contain" />
        {unreadCount > 0 && (
          <span
            className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-brand
                       text-[9px] font-bold text-white flex items-center justify-center leading-none
                       border border-surface-2"
            aria-label={`${unreadCount} unread notifications`}
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && createPortal(
        <div
          ref={portalRef}
          role="dialog"
          aria-label="Notifications"
          style={{
            position: 'fixed',
            top: `${coords.top + 8}px`,
            left: '50%',
            transform: 'translateX(-50%)',
            width: 'min(360px, calc(100vw - 1rem))',
          }}
          className="rounded-lg bg-surface-elevated border border-border
                     shadow-pop animate-fade-in z-[9999] overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-content">
                Notifications
              </span>
              {unreadCount > 0 && (
                <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-brand-soft text-brand">
                  {unreadCount}
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={markAllAsRead}
              disabled={unreadCount === 0}
              className="text-[11px] font-medium text-brand hover:underline
                         disabled:text-content-muted disabled:no-underline disabled:cursor-default
                         focus-ring rounded"
            >
              Mark all read
            </button>
          </div>

          {/* Body */}
          <div className="max-h-[60vh] overflow-y-auto">
            {isLoading && (
              <div className="flex items-center justify-center py-8">
                <span className="inline-block w-4 h-4 rounded-full border-2 border-brand border-t-transparent animate-spin" />
              </div>
            )}

            {!isLoading && isError && (
              <div className="px-4 py-8 flex flex-col items-center gap-2 text-center">
                <AlertTriangle size={20} className="text-warning" />
                <span className="text-xs text-content-muted">
                  Couldn&apos;t load notifications.
                </span>
              </div>
            )}

            {!isLoading && !isError && eventList.length === 0 && (
              <div className="px-4 py-10 flex flex-col items-center gap-2 text-center">
                <Inbox size={22} className="text-content-muted" />
                <span className="text-xs font-medium text-content">
                  You&apos;re all caught up
                </span>
                <span className="text-[11px] text-content-muted">
                  New events will appear here.
                </span>
              </div>
            )}

            {!isLoading && !isError && eventList.length > 0 && (
              <ul className="divide-y divide-border">
                {eventList.map((e, idx) => {
                  const id = getEventId(e) || String(idx);
                  const isUnread =
                    !lastSeenId ||
                    eventList.findIndex((x) => getEventId(x) === lastSeenId) > idx;
                  return (
                    <li
                      key={id}
                      className={`px-4 py-2.5 flex gap-2.5 items-start hover:bg-surface-2 transition-colors duration-fast ${
                        isUnread ? 'bg-surface-1' : ''
                      }`}
                    >
                      <span className="mt-0.5 flex-shrink-0">{severityIcon(e.severity)}</span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-content truncate">
                            {getEventTitle(e)}
                          </span>
                          {e.symbol && (
                            <span className="text-[10px] font-medium text-content-muted px-1.5 py-0.5 rounded bg-surface-3">
                              {e.symbol}
                            </span>
                          )}
                        </div>
                        {e.message && (
                          <p className="text-[11px] text-content-secondary mt-0.5 line-clamp-2">
                            {e.message}
                          </p>
                        )}
                        <span className="text-[10px] text-content-muted mt-1 inline-block">
                          {formatRelativeTime(getEventTime(e))}
                        </span>
                      </div>
                      {isUnread && (
                        <span
                          className={`mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${severityDotClass(e.severity)}`}
                          aria-hidden
                        />
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-border">
            <button
              type="button"
              onClick={goToJournal}
              className="w-full px-4 py-2.5 text-xs font-medium text-brand hover:bg-surface-2
                         transition-colors duration-fast focus-ring"
            >
              View all in Journal
            </button>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}

export const NotificationsPanel = memo(NotificationsPanelInner);
