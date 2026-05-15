import { useState, useEffect } from 'react';
import { useSymbols, useUpdateSymbols } from '@/features/symbols/api/symbols';
import { useTierGate } from '@/features/auth/hooks/useTierGate';
import { BarChart3, Check, ChevronRight } from 'lucide-react';

const SYMBOL_POOL_STORAGE_KEY = 'etradie-symbol-pool';

interface Props { onComplete: () => void; }

export function SymbolsStep({ onComplete }: Props) {
  const { data: symbolData } = useSymbols();
  const updateSymbols = useUpdateSymbols();
  const { isFree, openUpgradeModal } = useTierGate();

  const [selected, setSelected] = useState<string[]>([]);
  const [pool, setPool] = useState<string[]>([]);
  const [newSymbol, setNewSymbol] = useState('');

  const maxActiveSymbols = isFree ? 1 : Infinity;

  useEffect(() => {
    if (!symbolData) return;
    const active = symbolData.symbols || [];
    setSelected(isFree ? active.slice(0, 1) : active);

    let savedPool: string[] = [];
    try {
      savedPool = JSON.parse(localStorage.getItem(SYMBOL_POOL_STORAGE_KEY) || '[]');
    } catch {
      savedPool = [];
    }
    const combined = Array.from(new Set([...savedPool, ...active]));
    setPool(combined);
  }, [symbolData, isFree]);

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

  const addCustomSymbol = (e: React.FormEvent) => {
    e.preventDefault();
    const s = newSymbol.trim();
    if (!s || pool.includes(s)) {
      setNewSymbol('');
      return;
    }
    const newPool = [...pool, s];
    setPool(newPool);
    localStorage.setItem(SYMBOL_POOL_STORAGE_KEY, JSON.stringify(newPool));
    
    if (!(isFree && selected.length >= maxActiveSymbols)) {
      setSelected(p => [...p, s]);
    }
    setNewSymbol('');
  };

  const handleSave = async () => {
    try {
      await updateSymbols.mutateAsync(selected);
      onComplete();
    } catch { /* */ }
  };

  return (
    <div className="w-full max-w-lg mx-auto">
      <div className="text-center mb-8">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5 border border-white/10">
          <BarChart3 className="h-6 w-6 text-content" />
        </div>
        <h2 className="text-xl font-bold text-content">Pick your symbols</h2>
        <p className="mt-2 text-sm text-content-secondary">
          Select instruments for Exoper to monitor and analyze.
          {isFree && <span className="block text-brand mt-1">Free tier: 1 symbol limit</span>}
        </p>
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/5 p-6 space-y-6">
        <form onSubmit={addCustomSymbol} className="flex gap-2">
          <input
            type="text"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            placeholder="e.g. EURUSDm"
            className="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-content focus:border-white/30 focus:outline-none transition-colors"
          />
          <button type="submit" disabled={!newSymbol.trim()} className="rounded-xl bg-white px-4 py-2 text-sm font-bold text-black hover:bg-white/90 disabled:opacity-50 transition-colors">
            Add
          </button>
        </form>

        <div className="grid grid-cols-2 gap-3">
          {pool.map((s) => {
            const isSelected = selected.includes(s);
            return (
              <button
                key={s}
                type="button"
                onClick={() => toggleSymbol(s)}
                className={`flex items-center justify-between rounded-xl border p-3 transition-all duration-200
                  ${isSelected ? 'border-white/30 bg-white/10' : 'border-white/10 bg-white/[0.02] hover:border-white/20'}`}
              >
                <span className={`text-xs font-semibold ${isSelected ? 'text-white' : 'text-white/40'}`}>{s}</span>
                {isSelected && <Check size={14} className="text-success" />}
              </button>
            );
          })}
        </div>

        <button
          onClick={handleSave}
          disabled={updateSymbols.isPending || selected.length === 0}
          className="w-full rounded-xl bg-white p-3.5 text-sm font-bold text-black hover:bg-white/90 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
        >
          {updateSymbols.isPending ? 'Saving...' : <>Save symbols <ChevronRight size={16} /></>}
        </button>
      </div>
    </div>
  );
}
