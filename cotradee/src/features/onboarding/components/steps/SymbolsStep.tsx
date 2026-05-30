import { useState, useEffect, useMemo } from 'react';
import { useSymbols, useBrokerSymbols, useUpdateSymbols } from '@/features/symbols/api/symbols';
import { useTierGate } from '@/features/auth/hooks/useTierGate';
import { BarChart3, Check, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';

// One-time cleanup key. Old builds stored user-typed symbols here;
// the catalog-driven flow does not need it. Removing on mount so a
// returning user does not see ghost entries.
const LEGACY_SYMBOL_POOL_STORAGE_KEY = 'etradie-symbol-pool';

interface Props { onComplete: () => void; }

export function SymbolsStep({ onComplete }: Props) {
  const { data: symbolData } = useSymbols();
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
  const [picker, setPicker] = useState<string>('');

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

  const onPickFromDropdown = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const sym = e.target.value;
    // Reset the picker value to the placeholder option so the same
    // symbol can be re-picked (e.g. user unticks then re-ticks via
    // the dropdown).
    setPicker('');
    if (!sym) return;

    if (selected.includes(sym)) {
      // Already ticked - no-op; visible in the grid below.
      return;
    }
    if (isFree && selected.length >= maxActiveSymbols) {
      openUpgradeModal();
      return;
    }
    setSelected((prev) => [...prev, sym]);
  };

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
          <select
            value={picker}
            onChange={onPickFromDropdown}
            disabled={!catalogReady}
            className="w-full appearance-none rounded-xl border border-border bg-surface-3 px-4 py-2.5 pr-10 text-sm text-content focus:border-brand focus:outline-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="" disabled>
              {catalogLoading || !catalogReady
                ? 'Loading broker catalog\u2026'
                : 'Choose a symbol from your broker'}
            </option>
            {catalogSymbols.map((s) => (
              <option key={s.name} value={s.name}>
                {s.description ? `${s.name} \u2014 ${s.description}` : s.name}
              </option>
            ))}
          </select>
          {!catalogReady ? (
            <Loader2
              size={16}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-content-muted animate-spin pointer-events-none"
            />
          ) : (
            <ChevronDown
              size={16}
              strokeWidth={3}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-content-muted pointer-events-none"
            />
          )}
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
