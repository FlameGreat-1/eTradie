import { useState, useEffect, useRef, useMemo } from 'react';
import { Search, X, TrendingUp, Plus, Loader2 } from 'lucide-react';
import { useSymbols, useBrokerSymbols, useUpdateSymbols, type BrokerSymbol } from '@/features/symbols/api/symbols';

/**
 * Categorize a broker symbol based on its path string from MT5.
 * MT5 paths look like: "Forex\Majors", "Crypto\Bitcoin", "CFD\Indices", etc.
 */
function categorizeSymbol(sym: BrokerSymbol): string {
  const path = (sym.path || '').toLowerCase();
  const name = (sym.name || '').toLowerCase();
  
  if (path.includes('crypto') || path.includes('bitcoin') || path.includes('coin') || name.includes('usd') && (name.includes('btc') || name.includes('eth')))
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

const CATEGORIES = ['All', 'Forex', 'Crypto', 'Indices', 'Commodities', 'Stocks', 'Metals'];
const MAX_DISPLAY = 500;

interface SymbolSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (symbol: string) => void;
}

export function SymbolSearchModal({ isOpen, onClose, onSelect }: SymbolSearchModalProps) {
  const [query, setQuery] = useState('');
  const [activeTab, setActiveTab] = useState('All');
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: trackedData } = useSymbols();
  const { data: brokerData, isLoading: isBrokerLoading } = useBrokerSymbols();
  const updateSymbols = useUpdateSymbols();

  const trackedSymbols = trackedData?.symbols ?? [];
  const allBrokerSymbols = brokerData?.symbols ?? [];

  // Focus input when opened.
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setActiveTab('All');
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Handle escape key.
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Filter and categorize symbols.
  const filtered = useMemo(() => {
    let pool = allBrokerSymbols;

    // Category filter.
    if (activeTab !== 'All') {
      pool = pool.filter((s) => categorizeSymbol(s) === activeTab);
    }

    // Search query filter.
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      pool = pool.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q),
      );
    }

    // Limit display count for performance.
    return pool.slice(0, MAX_DISPLAY);
  }, [allBrokerSymbols, activeTab, query]);

  const queryStr = query.trim();
  const showAddButton =
    queryStr.length > 0 &&
    !allBrokerSymbols.some((s) => s.name.toLowerCase() === queryStr.toLowerCase());

  const handleAddAndSelect = async (sym: string) => {
    if (!sym || updateSymbols.isPending) return;
    try {
      if (!trackedSymbols.includes(sym)) {
        await updateSymbols.mutateAsync([...trackedSymbols, sym]);
      }
      onSelect(sym);
    } catch (err) {
      console.error('Failed to add symbol:', err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-sm p-4">
      {/* Click outside to close */}
      <div className="absolute inset-0" onClick={onClose} />

      <div className="relative w-full max-w-2xl bg-surface-1 rounded-xl shadow-2xl border border-border flex flex-col overflow-hidden animate-fade-in">
        {/* Header / Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-surface-2/50">
          <Search size={20} className="text-content-muted" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Symbol search..."
            className="flex-1 bg-transparent border-none outline-none text-lg text-content placeholder:text-content-muted"
          />
          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-surface-3 text-content-muted hover:text-content transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Categories / Tabs */}
        <div className="flex items-center gap-6 px-4 border-b border-border text-sm overflow-x-auto no-scrollbar">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveTab(cat)}
              className={`py-2 whitespace-nowrap transition-colors ${
                activeTab === cat
                  ? 'text-brand font-medium border-b-2 border-brand'
                  : 'text-content-muted hover:text-content'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Symbol List */}
        <div className="flex-1 overflow-y-auto max-h-[50vh] p-2">
          {isBrokerLoading ? (
            <div className="flex items-center justify-center py-12 text-content-muted gap-2">
              <Loader2 size={20} className="animate-spin" />
              <span>Loading broker instruments...</span>
            </div>
          ) : filtered.length === 0 && !showAddButton ? (
            <div className="text-center py-12 text-content-muted">
              No symbols match your search.
            </div>
          ) : (
            <>
              {filtered.map((sym) => (
                <button
                  key={sym.name}
                  onClick={() => handleAddAndSelect(sym.name)}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-lg hover:bg-surface-2 transition-colors text-left group"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded-full bg-surface-3 flex items-center justify-center text-brand">
                      <TrendingUp size={16} />
                    </div>
                    <div>
                      <div className="font-bold text-content group-hover:text-brand transition-colors">
                        {sym.name}
                      </div>
                      <div className="text-xs text-content-muted">
                        {sym.description || categorizeSymbol(sym)}
                      </div>
                    </div>
                  </div>
                  {trackedSymbols.includes(sym.name) && (
                    <span className="text-[10px] text-brand font-bold uppercase">Tracked</span>
                  )}
                </button>
              ))}

              {/* Add Custom Symbol Button */}
              {showAddButton && (
                <button
                  onClick={() => handleAddAndSelect(queryStr)}
                  disabled={updateSymbols.isPending}
                  className="w-full mt-2 flex items-center justify-between px-4 py-3 rounded-lg border border-dashed border-border hover:border-brand hover:bg-surface-2 transition-colors text-left group disabled:opacity-50"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded-full bg-brand/10 flex items-center justify-center text-brand">
                      <Plus size={16} />
                    </div>
                    <div>
                      <div className="font-bold text-brand">
                        Add "{queryStr}"
                      </div>
                      <div className="text-xs text-content-muted">
                        Press to track this custom broker symbol
                      </div>
                    </div>
                  </div>
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
