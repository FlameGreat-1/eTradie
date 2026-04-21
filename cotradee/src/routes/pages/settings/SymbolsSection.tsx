import { useState, useEffect } from 'react';
import { useSymbols, useUpdateSymbols } from '@/features/symbols/api/symbols';
import { useSystemConfig, useUpdateInterval } from '@/features/system/api/systemConfig';
import { Plus, Save, Trash2 } from 'lucide-react';

export default function SymbolsSection() {
  const { data: symbolData } = useSymbols();
  const { data: config } = useSystemConfig();
  const updateSymbols = useUpdateSymbols();
  const updateInterval = useUpdateInterval();

  const [selected, setSelected] = useState<string[]>([]);
  const [pool, setPool] = useState<string[]>([]);
  const [newSymbol, setNewSymbol] = useState('');
  const [intervalMins, setIntervalMins] = useState(120);

  // Sync when data arrives
  useEffect(() => {
    if (symbolData) {
      const active = symbolData.symbols || [];
      setSelected(active);
      
      const savedPool = JSON.parse(localStorage.getItem('etradie-symbol-pool') || '[]');
      const combined = Array.from(new Set([...savedPool, ...active]));
      setPool(combined);
      localStorage.setItem('etradie-symbol-pool', JSON.stringify(combined));
    }
  }, [symbolData]);

  useEffect(() => {
    if (config) {
      setIntervalMins(Math.round(config.cycle_interval_seconds / 60));
    }
  }, [config]);

  const toggleSymbol = (s: string) => {
    setSelected((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));
  };

  const removeSymbolFromPool = (s: string) => {
    const newPool = pool.filter((x) => x !== s);
    setPool(newPool);
    localStorage.setItem('etradie-symbol-pool', JSON.stringify(newPool));
    
    // Also remove from active selection if it was selected
    if (selected.includes(s)) {
      setSelected((prev) => prev.filter((x) => x !== s));
    }
  };

  const addCustomSymbol = (e: React.FormEvent) => {
    e.preventDefault();
    const s = newSymbol.trim();
    if (s && !pool.includes(s)) {
      const newPool = [...pool, s];
      setPool(newPool);
      localStorage.setItem('etradie-symbol-pool', JSON.stringify(newPool));
      // Optionally auto-select it when added
      setSelected((prev) => [...prev, s]);
    }
    setNewSymbol('');
  };

  return (
    <div className="space-y-8 max-w-lg">
      {/* Symbol Selection */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-content">Active Symbols</h3>
          <span className="text-xs text-content-muted">Add exact broker symbols</span>
        </div>
        
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
            {pool.map((s) => (
              <div key={s} className="flex items-center justify-between group">
                <label className="flex items-center gap-2 cursor-pointer text-xs text-content flex-1">
                  <input
                    type="checkbox"
                    checked={selected.includes(s)}
                    onChange={() => toggleSymbol(s)}
                    className="rounded border-border text-brand focus:ring-brand"
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
            ))}
            {pool.length === 0 && (
              <div className="col-span-2 text-center text-xs text-content-muted py-4">
                No symbols added yet.
              </div>
            )}
          </div>
          
          <div className="pt-2">
            <button
              onClick={() => updateSymbols.mutate(selected)}
              disabled={updateSymbols.isPending}
              className="flex items-center gap-1.5 rounded-lg bg-brand px-4 py-2 text-xs font-semibold text-white
                         hover:bg-brand-dark disabled:opacity-50 transition-colors w-full justify-center"
            >
              <Save size={14} /> {updateSymbols.isPending ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </div>
      </section>

      {/* Cycle Interval */}
      <section>
        <h3 className="text-sm font-semibold text-content mb-4">Cycle Interval</h3>
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
      </section>
    </div>
  );
}
