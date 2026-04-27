import { memo, useState, useCallback } from 'react';
import { useSymbols, useUpdateSymbols } from '@/features/symbols/api/symbols';
import { ChevronRight, ChevronLeft, Plus, X, Search } from 'lucide-react';

interface WatchlistSidebarProps {
  activeSymbol: string;
  onSymbolSelect: (symbol: string) => void;
}

function WatchlistSidebarInner({ activeSymbol, onSymbolSelect }: WatchlistSidebarProps) {
  const { data: symbolData } = useSymbols();
  const updateSymbols = useUpdateSymbols();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [searchFilter, setSearchFilter] = useState('');

  const symbols = symbolData?.symbols ?? [];
  const filteredSymbols = searchFilter
    ? symbols.filter((s: string) => s.toLowerCase().includes(searchFilter.toLowerCase()))
    : symbols;

  const handleAddSymbol = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const s = newSymbol.trim().toUpperCase();
      if (s && !symbols.includes(s)) {
        updateSymbols.mutate([...symbols, s]);
      }
      setNewSymbol('');
    },
    [newSymbol, symbols, updateSymbols],
  );

  const handleRemoveSymbol = useCallback(
    (sym: string) => {
      updateSymbols.mutate(symbols.filter((s: string) => s !== sym));
    },
    [symbols, updateSymbols],
  );

  if (isCollapsed) {
    return (
      <div
        className="flex flex-col items-center justify-start h-full border-l border-border
                    bg-surface-1 transition-all duration-base ease-out-expo"
        style={{ width: 36 }}
      >
        <button
          onClick={() => setIsCollapsed(false)}
          className="flex items-center justify-center w-full h-10 hover:bg-surface-2
                     text-content-muted hover:text-content transition-colors duration-fast focus-ring"
          title="Expand watchlist"
          aria-label="Expand watchlist"
        >
          <ChevronLeft size={14} />
        </button>
        <span
          className="text-[9px] font-bold text-content-muted uppercase tracking-widest mt-4"
          style={{ writingMode: 'vertical-rl', textOrientation: 'mixed' }}
          aria-hidden
        >
          Watchlist
        </span>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col h-full border-l border-border bg-surface-1
                  transition-all duration-base ease-out-expo overflow-hidden"
      style={{ width: 260 }}
      aria-label="Watchlist"
    >
      <div className="flex items-center justify-between px-3 h-10 border-b border-border flex-shrink-0">
        <span className="text-xs font-bold text-content uppercase tracking-wider">Watchlist</span>
        <button
          onClick={() => setIsCollapsed(true)}
          className="flex items-center justify-center w-6 h-6 rounded hover:bg-surface-2
                     text-content-muted hover:text-content transition-colors duration-fast focus-ring"
          title="Collapse watchlist"
          aria-label="Collapse watchlist"
        >
          <ChevronRight size={14} />
        </button>
      </div>

      <div className="px-3 py-2 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-1.5 rounded-lg bg-surface-2 border border-border px-2.5 h-7">
          <Search size={12} className="text-content-muted flex-shrink-0" />
          <input
            type="text"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            placeholder="Filter symbols…"
            className="bg-transparent border-none outline-none text-xs text-content placeholder:text-content-muted w-full focus-ring"
            aria-label="Filter symbols"
          />
        </div>
      </div>

      <form
        onSubmit={handleAddSymbol}
        className="px-3 py-2 border-b border-border flex-shrink-0"
      >
        <div className="flex items-center gap-1.5">
          <input
            type="text"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            placeholder="Add symbol…"
            className="flex-1 rounded-lg bg-surface-2 border border-border px-2.5 h-7
                       text-xs text-content placeholder:text-content-muted focus:border-brand focus-ring"
            aria-label="Add symbol"
          />
          <button
            type="submit"
            disabled={!newSymbol.trim()}
            className="flex items-center justify-center w-7 h-7 rounded-lg bg-brand-soft
                       text-brand hover:bg-brand-soft-strong transition-colors duration-fast disabled:opacity-30 focus-ring"
            aria-label="Add symbol to watchlist"
          >
            <Plus size={14} />
          </button>
        </div>
      </form>

      <div className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin">
        {filteredSymbols.length === 0 && (
          <div className="px-3 py-6 text-center text-xs text-content-muted">
            {symbols.length === 0 ? 'No symbols added yet.' : 'No matching symbols.'}
          </div>
        )}
        {filteredSymbols.map((sym: string) => {
          const isActive = sym === activeSymbol;
          return (
            <div
              key={sym}
              className={`group w-full flex items-center justify-between transition-colors duration-fast border-b border-border-subtle
                          ${
                            isActive
                              ? 'bg-brand-soft border-l-2 border-l-brand'
                              : 'hover:bg-surface-2 border-l-2 border-l-transparent'
                          }`}
            >
              <button
                type="button"
                onClick={() => onSymbolSelect(sym)}
                className="flex-1 flex items-center gap-2 px-3 py-2.5 text-left min-w-0 focus-ring"
              >
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    isActive ? 'bg-brand' : 'bg-content-faint'
                  }`}
                  aria-hidden
                />
                <span
                  className={`text-xs font-semibold truncate ${
                    isActive ? 'text-brand' : 'text-content'
                  }`}
                >
                  {sym}
                </span>
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleRemoveSymbol(sym);
                }}
                className="flex-shrink-0 mr-2 opacity-0 group-hover:opacity-100 transition-opacity duration-fast
                           text-content-muted hover:text-danger p-1 focus-ring rounded"
                title={`Remove ${sym}`}
                aria-label={`Remove ${sym} from watchlist`}
              >
                <X size={12} />
              </button>
            </div>
          );
        })}
      </div>

      <div className="px-3 py-2 border-t border-border flex-shrink-0">
        <span className="text-[10px] text-content-muted">
          {symbols.length} symbol{symbols.length !== 1 ? 's' : ''} active
        </span>
      </div>
    </div>
  );
}

export const WatchlistSidebar = memo(WatchlistSidebarInner);
