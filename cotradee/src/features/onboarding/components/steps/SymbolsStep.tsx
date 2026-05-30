import { useState, useEffect, useMemo } from 'react';
import { useSymbols, useBrokerSymbols, useUpdateSymbols } from '@/features/symbols/api/symbols';
import { useActiveBrokerConnection } from '@/features/broker/api/brokerConnections';
import { useTierGate } from '@/features/auth/hooks/useTierGate';
import { BarChart3, Check, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { SymbolCombobox } from '@/features/symbols/components/SymbolCombobox';

// One-time cleanup key. Old builds stored user-typed symbols here;
// the catalog-driven flow does not need it. Removing on mount so a
// returning user does not see ghost entries.
const LEGACY_SYMBOL_POOL_STORAGE_KEY = 'etradie-symbol-pool';

interface Props { onComplete: () => void; }

export function SymbolsStep({ onComplete }: Props) {
  const { data: symbolData } = useSymbols();
  
  // Get active connection to check provisioning status
  const { data: activeBrokerConn, isLoading: activeBrokerLoading } = useActiveBrokerConnection(
    undefined, 
    { refetchInterval: (query) => query.state.data?.connection?.status === 'provisioning' ? 3000 : false }
  );
  
  // The catalog is populated asynchronously by BrokerSyncService
  // immediately after step 0 (BrokerStep) succeeds. On a slow broker
  // this can take up to a minute. Poll every 3 s while the list is
  // empty so the dropdown fills in as soon as the broker reports
  // its first symbol. As soon as we have data, refetchInterval
  // returns false and the poll stops.
  const {
    data: brokerCatalog,
    isLoading: catalogLoading,
  } = useBrokerSymbols({
    refetchInterval: (query) => {
      const count = query.state.data?.symbols.length ?? 0;
      return count === 0 ? 3000 : false;
    },
  });
  const updateSymbols = useUpdateSymbols();
  const { isFree, openUpgradeModal } = useTierGate();

  const [selected, setSelected] = useState<string[]>([]);

  const maxActiveSymbols = isFree ? 1 : Infinity;

  // One-time legacy cleanup.
  useEffect(() => {
    try {
      localStorage.removeItem(LEGACY_SYMBOL_POOL_STORAGE_KEY);
    } catch {
      // localStorage unavailable (private-browsing edge case) - no-op.
    }
  }, []);

  // Seed the selected list from the user's saved active symbols. Free
  // tier caps at 1 by truncating; Pro keeps all.
  useEffect(() => {
    if (!symbolData) return;
    const active = symbolData.symbols || [];
    setSelected(isFree ? active.slice(0, 1) : active);
  }, [symbolData, isFree]);

  // The grid below the dropdown shows the union of:
  //   - everything the user has currently ticked (so a previously-saved
  //     symbol that is no longer in the broker catalog still renders
  //     and the user can untick it),
  //   - plus everything in the broker catalog that the user has ticked.
  //
  // We sort the union alphabetically for stable rendering.
  const pool = useMemo(() => {
    return Array.from(new Set(selected)).sort((a, b) => a.localeCompare(b));
  }, [selected]);

  const catalogSymbols = brokerCatalog?.symbols ?? [];
  const catalogReady = catalogSymbols.length > 0;


  const toggleSymbol = (s: string) => {
    setSelected((prev) => {
      if (prev.includes(s)) return prev.filter((x) => x !== s);
      if (isFree && prev.length >= maxActiveSymbols) {
        openUpgradeModal();
        return prev;
      }
      return [...prev, s];
    });
  };

  const handleSave = async () => {
    try {
      await updateSymbols.mutateAsync(selected);
      onComplete();
    } catch { /* surface via mutation state if needed */ }
  };

  const isProvisioning = activeBrokerConn?.connection?.status === 'provisioning';

  if (activeBrokerLoading || isProvisioning) {
    return (
      <div className="w-full max-w-lg mx-auto flex flex-col items-center justify-center py-12 space-y-6 text-center">
        <Loader2 size={40} className="text-brand animate-spin" />
        <div>
          <h2 className="text-xl font-bold text-content">Connecting to your broker...</h2>
          <p className="mt-2 text-sm text-content-secondary max-w-sm mx-auto">
            {activeBrokerConn?.connection?.status_message || 'Please wait while we provision your dedicated MetaTrader terminal. This may take up to 3 minutes.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-lg mx-auto">
      <div className="text-center mb-8">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-2 border border-border">
          <BarChart3 className="h-6 w-6 text-content" />
        </div>
        <h2 className="text-xl font-bold text-content">Pick your symbols</h2>
        <p className="mt-2 text-sm text-content-secondary">
          Select instruments for Exoper to monitor and analyze.
          {isFree && <span className="block text-brand mt-1">Free tier: 1 symbol limit</span>}
        </p>
      </div>

      <div className="rounded-2xl border border-border bg-surface-2 p-4 sm:p-6 space-y-6">
        {/*
          Catalog-driven dropdown. Replaces the previous free-text
          input. The user can only pick from what the broker actually
          publishes - no manual entry, no need to know the broker's
          naming convention.
        */}
        <div className="relative">
          <SymbolCombobox
            symbols={catalogSymbols}
            isLoading={catalogLoading || !catalogReady}
            onSelect={(sym) => {
              if (selected.includes(sym)) return;
              if (isFree && selected.length >= maxActiveSymbols) {
                openUpgradeModal();
                return;
              }
              setSelected((prev) => [...prev, sym]);
            }}
            disabled={!catalogReady}
            triggerClassName="w-full flex items-center justify-between appearance-none rounded-xl border border-border bg-surface-3 px-4 py-2.5 text-sm font-bold text-content focus:border-brand focus:outline-none transition-colors"
            dropdownClassName="border-border bg-surface-3 shadow-2xl"
          />
        </div>

        {/*
          Grid of ticked symbols. Visual contract preserved from the
          previous implementation: 2-column grid, brand-highlighted
          card when ticked, Check icon, click-to-untick.
        */}
        {pool.length > 0 ? (
          <div className="grid grid-cols-2 gap-2 sm:gap-3">
            {pool.map((s) => {
              const isSelected = selected.includes(s);
              return (
                <button
                  key={s}
                  type="button"
                  onClick={() => toggleSymbol(s)}
                  className={`flex items-center justify-between rounded-xl border p-2.5 sm:p-3 transition-all duration-200
                    ${isSelected ? 'border-brand bg-brand/10' : 'border-border bg-surface-1 hover:border-brand/30'}`}
                >
                  <span className={`text-xs font-semibold ${isSelected ? 'text-content' : 'text-content-muted'}`}>{s}</span>
                  {isSelected && <Check size={14} className="text-success" />}
                </button>
              );
            })}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-border bg-surface-1 px-4 py-6 text-center text-xs text-content-muted">
            Pick a symbol from the dropdown above to add it here.
          </div>
        )}

        <button
          onClick={handleSave}
          disabled={updateSymbols.isPending || selected.length === 0}
          className="w-full rounded-xl bg-black dark:bg-white p-3.5 text-sm font-bold text-white dark:text-black hover:opacity-90 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
        >
          {updateSymbols.isPending ? 'Saving...' : <>Save symbols <ChevronRight size={16} /></>}
        </button>
      </div>
    </div>
  );
}
