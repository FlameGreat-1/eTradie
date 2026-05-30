import { useState, useRef, useEffect, useMemo } from 'react';
import { Search, ChevronDown, Loader2 } from 'lucide-react';
import { BrokerSymbol } from '../api/symbols';

type GroupKey = 'Forex' | 'Crypto' | 'Indices' | 'Commodities' | 'Stocks' | 'Metals';

const GROUP_ORDER: GroupKey[] = ['Forex', 'Crypto', 'Indices', 'Commodities', 'Stocks', 'Metals'];

function categorizeSymbol(sym: BrokerSymbol): GroupKey {
  const path = (sym.path || '').toLowerCase();
  const name = (sym.name || '').toLowerCase();
  
  if (path.includes('crypto') || path.includes('bitcoin') || path.includes('coin') || (name.includes('usd') && (name.includes('btc') || name.includes('eth'))))
    return 'Crypto';
  if (path.includes('metal') || path.includes('gold') || path.includes('silver') || path.includes('xau') || path.includes('xag'))
    return 'Metals';
  if (path.includes('ind') || path.includes('index'))
    return 'Indices';
  if (path.includes('commodit') || path.includes('energy') || path.includes('energies') || path.includes('oil') || name.includes('xng') || name.includes('gas'))
    return 'Commodities';
  if (path.includes('stock') || path.includes('equit') || path.includes('shares'))
    return 'Stocks';
    
  return 'Forex'; // Default fallback
}

interface Props {
  symbols: BrokerSymbol[];
  isLoading: boolean;
  onSelect: (symbolName: string) => void;
  disabled?: boolean;
  triggerClassName?: string;
  dropdownClassName?: string;
}

export function SymbolCombobox({
  symbols,
  isLoading,
  onSelect,
  disabled,
  triggerClassName = "w-full flex items-center justify-between rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-2.5 text-sm font-bold text-black dark:text-white transition-all focus:border-brand outline-none",
  dropdownClassName = "bg-white dark:bg-black border border-black/10 dark:border-white/10"
}: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
      return () => document.removeEventListener('mousedown', handleOutsideClick);
    }
  }, [isOpen]);

  const [limit, setLimit] = useState(50);

  // Reset limit when search changes
  useEffect(() => {
    setLimit(50);
  }, [search]);

  const groupedAndFiltered = useMemo(() => {
    if (symbols.length === 0) return null;
    const needle = search.trim().toLowerCase();
    
    // Filter
    let filtered = symbols;
    if (needle) {
      filtered = symbols.filter(s => 
        s.name.toLowerCase().includes(needle) || 
        (s.description || '').toLowerCase().includes(needle)
      );
    }
    
    const isTruncated = filtered.length > limit;
    if (isTruncated) {
      filtered = filtered.slice(0, limit);
    }

    // Group
    const groups: Record<GroupKey, BrokerSymbol[]> = {
      Forex: [], Crypto: [], Indices: [], Commodities: [], Stocks: [], Metals: [],
    };
    for (const s of filtered) groups[categorizeSymbol(s)].push(s);
    for (const k of GROUP_ORDER) groups[k].sort((a, b) => a.name.localeCompare(b.name));

    return { groups, isTruncated };
  }, [symbols, search, limit]);

  const toggleOpen = () => {
    if (disabled || isLoading || symbols.length === 0) return;
    setIsOpen(!isOpen);
    if (!isOpen) {
      setSearch('');
      setLimit(50);
    }
  };

  const handleSelect = (name: string) => {
    onSelect(name);
    setIsOpen(false);
    setSearch('');
    setLimit(50);
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    // Load more when user scrolls within 50px of the bottom
    if (scrollHeight - scrollTop - clientHeight < 50) {
      setLimit(prev => prev + 50);
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={toggleOpen}
        disabled={disabled || isLoading || symbols.length === 0}
        className={`${triggerClassName} ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        <span className="truncate">
          {isLoading ? 'Loading broker catalogue…' : 
            symbols.length === 0 ? 'No symbols available' : 'Choose a Symbol'}
        </span>
        {isLoading ? (
          <Loader2 size={16} className="text-black/20 dark:text-white/20 animate-spin flex-shrink-0 ml-2" />
        ) : (
          <ChevronDown size={16} strokeWidth={3} className={`text-black/30 dark:text-white/30 transition-transform flex-shrink-0 ml-2 ${isOpen ? 'rotate-180' : ''}`} />
        )}
      </button>

      {isOpen && (
        <div className={`absolute top-full left-0 right-0 z-50 mt-2 rounded-xl shadow-xl overflow-hidden flex flex-col max-h-[350px] ${dropdownClassName}`}>
          <div className="p-2 border-b border-black/5 dark:border-white/5 shrink-0">
            <div className="relative">
              <Search size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-black/30 dark:text-white/30" />
              <input 
                type="text" 
                autoFocus
                placeholder="Search symbol or description..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-black/5 dark:bg-white/5 border border-transparent focus:border-brand focus:bg-white dark:focus:bg-black rounded-lg py-2 pl-10 pr-3 text-sm font-bold text-black dark:text-white placeholder:font-normal placeholder:text-black/30 dark:placeholder:text-white/30 outline-none transition-all"
              />
            </div>
          </div>
          
          <div className="overflow-y-auto p-2 space-y-3 flex-1 custom-scrollbar" onScroll={handleScroll}>
            {groupedAndFiltered && GROUP_ORDER.map((group) => {
              const items = groupedAndFiltered.groups[group];
              if (items.length === 0) return null;
              
              return (
                <div key={group}>
                  <div className="px-2 py-1 mb-1 text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30 sticky top-0 bg-white/95 dark:bg-black/95 backdrop-blur z-10">
                    {group}
                  </div>
                  <div className="space-y-0.5">
                    {items.map((s) => (
                      <button
                        key={s.name}
                        onClick={() => handleSelect(s.name)}
                        className="w-full text-left px-2 py-1.5 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 transition-colors group flex items-center justify-between"
                      >
                        <div className="flex flex-col">
                          <span className="text-sm font-bold text-black dark:text-white">{s.name}</span>
                          {s.description && (
                            <span className="text-[10px] font-medium text-black/40 dark:text-white/40 truncate">{s.description}</span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
            
            {groupedAndFiltered && Object.values(groupedAndFiltered.groups).every(arr => arr.length === 0) && (
              <div className="text-center py-8 text-xs font-medium text-black/40 dark:text-white/40">
                No symbols found for "{search}"
              </div>
            )}
            
            {/* If still truncated after scroll, show a subtle loading indicator at bottom */}
            {groupedAndFiltered?.isTruncated && (
              <div className="flex justify-center py-2">
                <Loader2 size={14} className="animate-spin text-black/20 dark:text-white/20" />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
