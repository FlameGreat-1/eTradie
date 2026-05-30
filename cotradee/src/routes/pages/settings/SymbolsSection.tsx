import { useEffect, useMemo, useState } from 'react';
import { Save, Check, ChevronDown, Loader2 } from 'lucide-react';

import ProFeatureLock from '@/components/ui/ProFeatureLock';
import { useTierGate } from '@/features/auth/hooks/useTierGate';
import {
  useBrokerSymbols,
  useSymbols,
  useUpdateSymbols,
} from '@/features/symbols/api/symbols';
import { SymbolCombobox } from '@/features/symbols/components/SymbolCombobox';
import { useSystemConfig, useUpdateInterval } from '@/features/system/api/systemConfig';

export default function SymbolsSection() {
  const { data: activeData } = useSymbols();
  const { data: brokerCatalog, isLoading: catalogLoading } = useBrokerSymbols();
  const { data: config } = useSystemConfig();
  const updateSymbols = useUpdateSymbols();
  const updateInterval = useUpdateInterval();
  const { isFree, copy, openUpgradeModal } = useTierGate();

  const [selected, setSelected] = useState<string[]>([]);
  const [intervalMins, setIntervalMins] = useState(120);

  const maxActiveSymbols = isFree ? 1 : Infinity;
  const gateCopy = copy('symbols');

  useEffect(() => {
    const active = activeData?.symbols ?? [];
    setSelected(isFree ? active.slice(0, 1) : active);
  }, [activeData, isFree]);

  useEffect(() => {
    if (config) setIntervalMins(Math.round(config.cycle_interval_seconds / 60));
  }, [config]);

  const pool = useMemo(() => {
    return Array.from(new Set(selected)).sort((a, b) => a.localeCompare(b));
  }, [selected]);

  const catalogSymbols = brokerCatalog?.symbols ?? [];
  const catalogReady = catalogSymbols.length > 0;


  const toggleSymbol = (name: string) => {
    setSelected((prev) => {
      if (prev.includes(name)) return prev.filter((x) => x !== name);
      if (isFree && prev.length >= maxActiveSymbols) {
        openUpgradeModal();
        return prev;
      }
      return [...prev, name];
    });
  };

  const save = () => {
    const payload = isFree ? selected.slice(0, maxActiveSymbols) : selected;
    updateSymbols.mutate(payload);
  };

  return (
    <div className="space-y-10 max-w-lg">
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex flex-col gap-0.5">
            <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">Configuration</div>
            <h3 className="text-base font-bold text-black dark:text-white tracking-tight">Active Symbols</h3>
          </div>
          <span className="text-[10px] font-black uppercase tracking-widest text-black/30 dark:text-white/30">
            {isFree ? `${selected.length} / 1 selected` : `${selected.length} selected`}
          </span>
        </div>

        {isFree && (
          <div role="status" className="mb-6 rounded-2xl border border-brand/20 bg-brand/5 p-4 shadow-sm">
            <p className="text-[11px] font-bold text-black/60 dark:text-white/60 leading-relaxed">{gateCopy.body}</p>
            <button
              type="button"
              onClick={openUpgradeModal}
              className="mt-3 inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-brand hover:opacity-80 transition-all"
            >
              Upgrade to Pro
            </button>
          </div>
        )}

        <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.01] dark:bg-white/[0.02] p-6 space-y-6 shadow-sm">
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
              triggerClassName="w-full flex items-center justify-between rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black px-4 py-2.5 text-sm font-bold text-black dark:text-white transition-all focus:border-brand outline-none"
              dropdownClassName="bg-white dark:bg-black border border-black/10 dark:border-white/10"
            />
          </div>

          {pool.length > 0 ? (
            <div className="grid grid-cols-2 gap-2">
              {pool.map((s) => {
                const isSelected = selected.includes(s);
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleSymbol(s)}
                    className={`flex items-center justify-between rounded-xl border p-2.5 sm:p-3 transition-all duration-200
                      ${isSelected ? 'border-brand bg-brand/5 dark:bg-brand/10' : 'border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] hover:border-brand/30'}`}
                  >
                    <span className={`text-xs font-bold tracking-tight ${isSelected ? 'text-black dark:text-white' : 'text-black/60 dark:text-white/60'}`}>{s}</span>
                    {isSelected && <Check size={14} className="text-brand" />}
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] px-4 py-6 text-center text-[11px] font-bold text-black/30 dark:text-white/30">
              Pick a symbol from the dropdown above to add it here.
            </div>
          )}

          <div className="pt-2">
            <button
              onClick={save}
              disabled={updateSymbols.isPending || selected.length === 0}
              className="flex items-center gap-2 rounded-xl bg-black dark:bg-white px-12 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40 w-fit"
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
              className="flex items-center gap-2 rounded-xl bg-black dark:bg-white px-12 py-3 text-[10px] font-black uppercase tracking-widest text-white dark:text-black hover:opacity-90 shadow-lg shadow-black/10 dark:shadow-white/10 transition-all disabled:opacity-40"
            >
              <Save size={14} strokeWidth={3} /> {updateInterval.isPending ? 'Saving…' : 'Update Interval'}
            </button>
          </div>
        </ProFeatureLock>
      </section>
    </div>
  );
}
