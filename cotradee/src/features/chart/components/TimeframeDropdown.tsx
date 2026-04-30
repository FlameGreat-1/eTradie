import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Check } from 'lucide-react';

interface TimeframeDropdownProps {
  value: string;
  onChange: (tf: string) => void;
}

const CATEGORIES = [
  {
    name: 'Minutes',
    items: [
      { id: 'M1', label: '1 minute' },
      { id: 'M5', label: '5 minutes' },
      { id: 'M15', label: '15 minutes' },
      { id: 'M30', label: '30 minutes' },
    ],
  },
  {
    name: 'Hours',
    items: [
      { id: 'H1', label: '1 hour' },
      { id: 'H3', label: '3 hours' },
      { id: 'H4', label: '4 hours' },
      { id: 'H6', label: '6 hours' },
      { id: 'H8', label: '8 hours' },
      { id: 'H12', label: '12 hours' },
    ],
  },
  {
    name: 'Days/Months',
    items: [
      { id: 'D1', label: '1 day' },
      { id: 'W1', label: '1 week' },
      { id: 'MN1', label: '1 month' },
    ],
  },
];

export function TimeframeDropdown({ value, onChange }: TimeframeDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0, width: 0 });
  const menuRef = useRef<HTMLDivElement>(null);
  const portalRef = useRef<HTMLDivElement>(null);

  const toggle = () => {
    if (!isOpen && menuRef.current) {
      const rect = menuRef.current.getBoundingClientRect();
      setCoords({
        top: rect.bottom,
        left: rect.left + rect.width / 2,
        width: rect.width,
      });
    }
    setIsOpen(!isOpen);
  };

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      const clickedOutsideTrigger = menuRef.current && !menuRef.current.contains(target);
      const clickedOutsidePortal = portalRef.current && !portalRef.current.contains(target);
      
      if (clickedOutsideTrigger && clickedOutsidePortal) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handler);
    }
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  const handleSelect = (tf: string) => {
    onChange(tf);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={toggle}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        className={`flex items-center gap-1.5 px-3 h-8 rounded-md border border-border text-xs font-bold transition-colors duration-fast focus-ring
                    ${isOpen ? 'bg-surface-3 text-content' : 'text-content hover:bg-surface-3'}`}
      >
        <span>{value}</span>
        <ChevronDown
          size={14}
          className={`text-content-muted transition-transform duration-fast ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {isOpen && createPortal(
        <div
          ref={portalRef}
          role="listbox"
          style={{
            position: 'fixed',
            top: `${coords.top + 6}px`,
            left: '50%',
            transform: 'translateX(-50%)',
            width: '12rem', // Restore original w-48
          }}
          className="bg-surface-elevated border border-border
                     rounded-md shadow-pop py-1 z-[9999] animate-fade-in"
        >
          {CATEGORIES.map((cat, i) => (
            <div key={cat.name}>
              {i > 0 && <div className="h-px bg-border my-1" />}
              <div className="px-3 py-1 text-[10px] font-bold text-content-muted uppercase tracking-wider">
                {cat.name}
              </div>
              {cat.items.map((item) => (
                <button
                  type="button"
                  key={item.id}
                  onClick={() => handleSelect(item.id)}
                  className="w-full flex items-center justify-between px-3 py-1.5 text-sm text-left
                             hover:bg-surface-2 text-content transition-colors duration-fast focus-ring"
                  role="option"
                  aria-selected={value === item.id}
                >
                  <span>{item.label}</span>
                  {value === item.id && <Check size={14} className="text-brand" />}
                </button>
              ))}
            </div>
          ))}
        </div>,
        document.body
      )}
    </div>
  );
}
