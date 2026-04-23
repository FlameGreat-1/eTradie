import { useState, useRef, useEffect } from 'react';
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
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
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
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-1.5 px-3 h-8 rounded border border-border text-sm font-bold transition-colors ${
          isOpen
            ? 'bg-surface-3 text-content'
            : 'text-content hover:bg-surface-3'
        }`}
      >
        <span>{value}</span>
        <ChevronDown size={14} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-48 bg-surface-1 border border-border rounded-md shadow-xl z-[100] py-1">
          {CATEGORIES.map((cat, i) => (
            <div key={cat.name}>
              {i > 0 && <div className="h-px bg-border my-1" />}
              <div className="px-3 py-1 text-[10px] font-bold text-content-muted uppercase tracking-wider">
                {cat.name}
              </div>
              {cat.items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => handleSelect(item.id)}
                  className="w-full flex items-center justify-between px-3 py-1.5 text-sm text-left hover:bg-surface-2 text-content transition-colors"
                >
                  <span>{item.label}</span>
                  {value === item.id && <Check size={14} className="text-brand" />}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
