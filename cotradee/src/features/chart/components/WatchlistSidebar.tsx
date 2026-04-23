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

  // Collapsed state — show a thin toggle bar.
  if (isCollapsed) {
    return (
      <div
        className="flex flex-col items-center justify-start h-full border-l border-border
                    bg-surface-1 transition-all duration-300 ease-out"
        style={{ width: 36 }}
      >
        <button
          onClick={() => setIsCollapsed(false)}
          className="flex items-center justify-center w-full h-10 hover:bg-surface-2
                     text-content-muted hover:text-content transition-colors"
          title="Expand Watchlist"
        >
          <ChevronLeft size={14} />
        </button>
        {/* Vertical label */}
        <span
          className="text-[9px] font-bold text-content-muted uppercase tracking-widest mt-4"
          style={{ writingMode: 'vertical-rl', textOrientation: 'mixed' }}
        >
          Watchlist
        </span>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col h-full border-l border-border bg-surface-1
                  transition-all duration-300 ease-out overflow-hidden"
      style={{ width: 260 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 h-10 border-b border-border flex-shrink-0">
        <span className="text-xs font-bold text-content uppercase tracking-wider">Watchlist</span>
        <button
          onClick={() => setIsCollapsed(true)}
          className="flex items-center justify-center w-6 h-6 rounded hover:bg-surface-2
                     text-content-muted hover:text-content transition-colors"
          title="Collapse Watchlist"
        >
          <ChevronRight size={14} />
        </button>
      </div>

      {/* Search */}
      <div className="px-3 py-2 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-1.5 rounded-lg bg-surface-2 border border-border px-2.5 h-7">
          <Search size={12} className="text-content-muted flex-shrink-0" />
          <input
            type="text"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            placeholder="Filter symbols…"
            className="bg-transparent border-none outline-none text-xs text-content placeholder:text-content-muted w-full"
          />
        </div>
      </div>

      {/* Add symbol */}
      <form onSubmit={handleAddSymbol} className="px-3 py-2 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <input
            type="text"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            placeholder="Add symbol…"
            className="flex-1 rounded-lg bg-surface-2 border border-border px-2.5 h-7
                       text-xs text-content placeholder:text-content-muted focus:border-brand focus:outline-none"
          />
          <button
            type="submit"
            disabled={!newSymbol.trim()}
            className="flex items-center justify-center w-7 h-7 rounded-lg bg-brand/10
                       text-brand hover:bg-brand/20 transition-colors disabled:opacity-30"
          >
            <Plus size={14} />
          </button>
        </div>
      </form>

      {/* Symbol List */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin">
        {filteredSymbols.length === 0 && (
          <div className="px-3 py-6 text-center text-xs text-content-muted">
            {symbols.length === 0 ? 'No symbols added yet.' : 'No matching symbols.'}
          </div>
        )}
        {filteredSymbols.map((sym: string) => {
          const isActive = sym === activeSymbol;
          return (
            <button
              key={sym}
              onClick={() => onSymbolSelect(sym)}
              className={`group w-full flex items-center justify-between px-3 py-2.5 text-left
                         transition-all duration-150 border-b border-border/30
                         ${isActive
                           ? 'bg-brand/8 border-l-2 border-l-brand'
                           : 'hover:bg-surface-2 border-l-2 border-l-transparent'
                         }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                {/* Color dot */}
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    isActive ? 'bg-brand' : 'bg-content-muted/40'
                  }`}
                />
                <span
                  className={`text-xs font-semibold truncate ${
                    isActive ? 'text-brand' : 'text-content'
                  }`}
                >
                  {sym}
                </span>
              </div>
              {/* Remove button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleRemoveSymbol(sym);
                }}
                className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity
                           text-content-muted hover:text-danger p-0.5"
                title={`Remove ${sym}`}
              >
                <X size={12} />
              </button>
            </button>
          );
        })}
      </div>

      {/* Footer stats */}
      <div className="px-3 py-2 border-t border-border flex-shrink-0">
        <span className="text-[10px] text-content-muted">
          {symbols.length} symbol{symbols.length !== 1 ? 's' : ''} active
        </span>
      </div>
    </div>
  );
}

export const WatchlistSidebar = memo(WatchlistSidebarInner);
