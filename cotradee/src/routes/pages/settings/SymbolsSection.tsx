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
    <div className="space-y-10 max-w-lg">
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex flex-col gap-0.5">
            <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Configuration</div>
            <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Active Symbols</h3>
          </div>
          <span className="text-[10px] font-black uppercase tracking-widest">
            {isFree ? (
              <span className="text-black/20 dark:text-white/20">{selected.length} / 1 selected</span>
            ) : (
              <span className="text-brand border-b border-brand/30 pb-0.5">Add exact broker symbols</span>
            )}
          </span>
        </div>

        {isFree && (
          <div
            role="status"
            className="mb-6 rounded-2xl border border-brand/20 bg-brand/5 p-4 shadow-sm"
          >
            <p className="text-[11px] font-bold text-black/60 dark:text-white/60 leading-relaxed">
              {gateCopy.body}
            </p>
            <button
              type="button"
              onClick={openUpgradeModal}
              className="mt-3 inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-brand hover:opacity-80 transition-all"
            >
              Upgrade to Pro <Plus size={10} strokeWidth={4} />
            </button>
          </div>
        )}

        <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 space-y-6 shadow-sm">
          <form onSubmit={addCustomSymbol} className="flex items-center gap-2">
            <input
              type="text"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              placeholder="e.g. USDCHFm"
              className="flex-1 rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-2.5 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
            />
            <button
              type="submit"
              disabled={!newSymbol.trim()}
              className="flex items-center gap-1.5 rounded-xl bg-black dark:bg-white border border-transparent px-5 py-2.5 text-[10px] font-black uppercase tracking-widest text-white dark:text-black
                         hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-20"
            >
              <Plus size={14} strokeWidth={3} /> Add
            </button>
          </form>

          <div className="grid grid-cols-2 gap-4">
            {pool.map((s) => {
              const isSelected = selected.includes(s);
              const disabledForCap = isFree && !isSelected && limitReached;
              return (
                <div key={s} className="flex items-center justify-between group p-2 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 transition-all">
                  <label
                    className={`flex items-center gap-3 text-xs flex-1 ${
                      disabledForCap
                        ? 'cursor-not-allowed text-black/20 dark:text-white/20'
                        : 'cursor-pointer text-black/60 dark:text-white/60 font-bold'
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
                      className="h-4 w-4 rounded border-black/10 dark:border-white/10 text-brand focus:ring-brand disabled:opacity-20 transition-all cursor-pointer"
                    />
                    <span className="tracking-tight">{s}</span>
                  </label>
                  <button
                    onClick={() => removeSymbolFromPool(s)}
                    className="text-black/20 dark:text-white/20 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all p-1.5 rounded-md hover:bg-red-500/10"
                    title="Remove from pool"
                  >
                    <Trash2 size={12} strokeWidth={3} />
                  </button>
                </div>
              );
            })}
            {pool.length === 0 && (
              <div className="col-span-2 text-center text-[11px] font-bold text-black/20 dark:text-white/20 py-8 italic bg-black/5 dark:bg-white/5 rounded-xl border border-dashed border-black/10 dark:border-white/10">
                No symbols added yet.
              </div>
            )}
          </div>

          <div className="pt-2">
            <button
              onClick={() => {
                const payload = isFree
                  ? selected.slice(0, maxActiveSymbols)
                  : selected;
                updateSymbols.mutate(payload);
              }}
              disabled={updateSymbols.isPending || selected.length === 0}
              className="flex items-center gap-2 rounded-xl bg-black dark:bg-white px-12 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black
                         hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40 w-fit"
            >
              <Save size={14} strokeWidth={3} /> {updateSymbols.isPending ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </div>
      </section>

      <section>
        <div className="flex flex-col gap-0.5 mb-4">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Schedules</div>
          <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Cycle Interval</h3>
        </div>
        <ProFeatureLock feature="scheduling" variant="overlay">
          <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 space-y-4 shadow-sm">
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={1}
                max={1440}
                value={intervalMins}
                onChange={(e) => setIntervalMins(Number(e.target.value))}
                className="w-24 rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-2.5 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none"
              />
              <span className="text-[10px] font-black uppercase tracking-widest text-black/30 dark:text-white/30">minutes</span>
            </div>
            <button
              onClick={() => updateInterval.mutate(intervalMins * 60)}
              disabled={updateInterval.isPending}
              className="flex items-center gap-2 rounded-xl bg-black dark:bg-white px-12 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black
                         hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40"
            >
              <Save size={14} strokeWidth={3} /> {updateInterval.isPending ? 'Saving…' : 'Update Interval'}
            </button>
          </div>
        </ProFeatureLock>
      </section>
    </div>
  );
}
