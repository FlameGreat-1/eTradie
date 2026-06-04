import { useState, useRef } from 'react';
import { CalendarDays } from 'lucide-react';
import PnLCalendar from '@/features/journal/components/PnLCalendar';

export function FloatingCalendarButton() {
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ startX: number; startY: number; initX: number; initY: number; hasMoved: boolean } | null>(null);

  const onPointerDown = (e: React.PointerEvent<HTMLButtonElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initX: pos.x,
      initY: pos.y,
      hasMoved: false,
    };
  };

  const onPointerMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    if (!dragRef.current.hasMoved && (Math.abs(dx) > 3 || Math.abs(dy) > 3)) {
      dragRef.current.hasMoved = true;
    }
    if (dragRef.current.hasMoved) {
      setPos({ x: dragRef.current.initX + dx, y: dragRef.current.initY + dy });
    }
  };

  const onPointerUp = (e: React.PointerEvent<HTMLButtonElement>) => {
    e.currentTarget.releasePointerCapture(e.pointerId);
    if (dragRef.current && !dragRef.current.hasMoved) {
      setCalendarOpen(true);
    }
    dragRef.current = null;
  };

  return (
    <>
      {calendarOpen && <PnLCalendar onClose={() => setCalendarOpen(false)} />}
      <div
        className="fixed bottom-6 right-6 sm:bottom-8 sm:right-8 z-40 touch-none"
        style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}
      >
        <button
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          className="flex items-center justify-center w-14 h-14 rounded-2xl border border-border bg-white dark:bg-black text-content shadow-pop hover:scale-105 transition-all duration-300 group cursor-grab active:cursor-grabbing"
          aria-label="Open PnL Calendar"
          id="pnl-calendar-fab"
        >
          <CalendarDays size={24} className="group-hover:animate-pulse pointer-events-none text-brand" />
        </button>
      </div>
    </>
  );
}
