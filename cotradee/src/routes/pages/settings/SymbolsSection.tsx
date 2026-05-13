import { useState, useEffect, useMemo } from 'react';
import { Plus, Save, Trash2 } from 'lucide-react';
import { useSymbols, useUpdateSymbols } from '@/features/symbols/api/symbols';
import { useSystemConfig, useUpdateInterval } from '@/features/system/api/systemConfig';
import { useTierGate } from '@/features/auth/hooks/useTierGate';
import ProFeatureLock from '@/components/ui/ProFeatureLock';

// Storage key for the user's local symbol pool. Kept lowercase-only and
// namespaced so it never collides with another feature's storage.
const SYMBOL_POOL_STORAGE_KEY = 'etradie-symbol-pool';

export default function SymbolsSection() {
  const { data: symbolData } = useSymbols();
  const { data: config } = useSystemConfig();
  const updateSymbols = useUpdateSymbols();
  const updateInterval = useUpdateInterval();
  const { isFree, copy, openUpgradeModal } = useTierGate();

  const [selected, setSelected] = useState<string[]>([]);
  const [pool, setPool] = useState<string[]>([]);
  const [newSymbol, setNewSymbol] = useState('');
  const [intervalMins, setIntervalMins] = useState(120);

  // The product spec is unambiguous: Free tier is capped at exactly one
  // active symbol. We resolve this once per render so the UI logic stays
  // declarative below.
  const maxActiveSymbols = isFree ? 1 : Infinity;
  const gateCopy = copy('symbols');

  useEffect(() => {
    if (!symbolData) return;
    const active = symbolData.symbols || [];
    // If the backend has already truncated a downgraded user to one
    // symbol, reflect that immediately so the checkbox state is honest.
    const initialSelected = isFree ? active.slice(0, 1) : active;
    setSelected(initialSelected);

    let savedPool: string[] = [];
    try {
      savedPool = JSON.parse(localStorage.getItem(SYMBOL_POOL_STORAGE_KEY) || '[]');
    } catch {
      savedPool = [];
    }
    const combined = Array.from(new Set([...savedPool, ...active]));
    setPool(combined);
    try {
      localStorage.setItem(SYMBOL_POOL_STORAGE_KEY, JSON.stringify(combined));
    } catch {
      /* ignore quota errors; the pool is non-critical UI state */
    }
  }, [symbolData, isFree]);

  useEffect(() => {
    if (config) {
      setIntervalMins(Math.round(config.cycle_interval_seconds / 60));
    }
  }, [config]);

  const limitReached = useMemo(
    () => selected.length >= maxActiveSymbols,
    [selected.length, maxActiveSymbols],
  );

  const toggleSymbol = (s: string) => {
    setSelected((prev) => {
      const isCurrentlySelected = prev.includes(s);
      if (isCurrentlySelected) {
        return prev.filter((x) => x !== s);
      }
      // Adding a new symbol: enforce the Free-tier cap inline.
      if (isFree && prev.length >= maxActiveSymbols) {
        openUpgradeModal();
        return prev;
      }
      return [...prev, s];
    });
  };

  const removeSymbolFromPool = (s: string) => {
    const newPool = pool.filter((x) => x !== s);
    setPool(newPool);
    try {
      localStorage.setItem(SYMBOL_POOL_STORAGE_KEY, JSON.stringify(newPool));
    } catch {
      /* non-fatal */
    }

    if (selected.includes(s)) {
      setSelected((prev) => prev.filter((x) => x !== s));
    }
  };

  const addCustomSymbol = (e: React.FormEvent) => {
    e.preventDefault();
    const s = newSymbol.trim();
    if (!s || pool.includes(s)) {
      setNewSymbol('');
      return;
    }
    const newPool = [...pool, s];
    setPool(newPool);
    try {
      localStorage.setItem(SYMBOL_POOL_STORAGE_KEY, JSON.stringify(newPool));
    } catch {
      /* non-fatal */
    }

    // For Free users we never auto-select beyond the cap so the cap is
    // honoured immediately on add as well. Pro/admin auto-selects as before.
    setSelected((prev) => {
      if (isFree && prev.length >= maxActiveSymbols) {
        return prev;
      }
      return [...prev, s];
    });
    setNewSymbol('');
  };

  return (
    <div className="space-y-8 max-w-lg">
      <section>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-content">Active Symbols</h3>
          <span className="text-xs text-content-muted">
            {isFree
              ? `${selected.length} / 1 selected`
              : 'Add exact broker symbols'}
          </span>
        </div>

        {isFree && (
          <div
            role="status"
            className="mb-4 rounded-lg border border-brand/30 bg-brand/5 px-4 py-3"
          >
            <p className="text-[11px] text-content leading-relaxed">
              {gateCopy.body}
            </p>
            <button
              type="button"
              onClick={openUpgradeModal}
              className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-brand hover:underline transition-colors"
            >
              Upgrade to Pro →
            </button>
          </div>
        )}

        <div className="rounded-xl border border-border bg-surface-1 p-5 space-y-5">
          <form onSubmit={addCustomSymbol} className="flex items-center gap-2">
            <input
              type="text"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              placeholder="e.g. USDCHFm"
              className="flex-1 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-content
                         focus:border-brand focus:outline-none"
            />
            <button
              type="submit"
              disabled={!newSymbol.trim()}
              className="flex items-center gap-1.5 rounded-lg bg-surface-2 border border-border px-4 py-2 text-xs font-semibold text-content
                         hover:bg-surface-3 transition-colors disabled:opacity-50"
            >
              <Plus size={14} /> Add
            </button>
          </form>

          <div className="grid grid-cols-2 gap-3">
            {pool.map((s) => {
              const isSelected = selected.includes(s);
              // A Free user with the cap reached cannot tick a second box.
              // The current selection's box stays togglable so they can swap.
              const disabledForCap = isFree && !isSelected && limitReached;
              return (
                <div key={s} className="flex items-center justify-between group">
                  <label
                    className={`flex items-center gap-2 text-xs flex-1 ${
                      disabledForCap
                        ? 'cursor-not-allowed text-content-muted'
                        : 'cursor-pointer text-content'
                    }`}
                    title={
                      disabledForCap
                        ? gateCopy.body
                        : undefined
                    }
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={disabledForCap}
                      onChange={() => {
                        if (disabledForCap) {
                          openUpgradeModal();
                          return;
                        }
                        toggleSymbol(s);
                      }}
                      className="rounded border-border text-brand focus:ring-brand disabled:opacity-50"
                    />
                    {s}
                  </label>
                  <button
                    onClick={() => removeSymbolFromPool(s)}
                    className="text-content-muted hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity p-1"
                    title="Remove from pool"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              );
            })}
            {pool.length === 0 && (
              <div className="col-span-2 text-center text-xs text-content-muted py-4">
                No symbols added yet.
              </div>
            )}
          </div>

          <div className="pt-2">
            <button
              onClick={() => {
                // Final client-side guard: never PUT more than the cap.
                // The server enforces the same rule and is authoritative,
                // but pre-trimming gives the user a faster, clearer round-trip.
                const payload = isFree
                  ? selected.slice(0, maxActiveSymbols)
                  : selected;
                updateSymbols.mutate(payload);
              }}
              disabled={updateSymbols.isPending || selected.length === 0}
              className="flex items-center gap-1.5 rounded-lg bg-transparent border border-brand px-4 py-2 text-xs font-semibold text-brand
                         hover:bg-brand/5 disabled:opacity-50 transition-colors w-full justify-center"
            >
              <Save size={14} /> {updateSymbols.isPending ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-content mb-4">Cycle Interval</h3>
        <ProFeatureLock feature="scheduling" variant="overlay">
          <div className="rounded-xl border border-border bg-surface-1 p-5 space-y-3">
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={1}
                max={1440}
                value={intervalMins}
                onChange={(e) => setIntervalMins(Number(e.target.value))}
                className="w-24 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-content
                           focus:border-brand focus:outline-none"
              />
              <span className="text-xs text-content-muted">minutes</span>
            </div>
            <button
              onClick={() => updateInterval.mutate(intervalMins * 60)}
              disabled={updateInterval.isPending}
              className="flex items-center gap-1.5 rounded-lg bg-brand px-4 py-2 text-xs font-semibold text-white
                         hover:bg-brand-dark disabled:opacity-50 transition-colors"
            >
              <Save size={12} /> {updateInterval.isPending ? 'Saving…' : 'Update Interval'}
            </button>
          </div>
        </ProFeatureLock>
      </section>
    </div>
  );
}
