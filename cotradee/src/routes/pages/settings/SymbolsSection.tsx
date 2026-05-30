import { useEffect, useMemo, useState } from 'react';
import { Save, Search } from 'lucide-react';

import ProFeatureLock from '@/components/ui/ProFeatureLock';
import { useTierGate } from '@/features/auth/hooks/useTierGate';
import {
  BrokerSymbol,
  useBrokerSymbols,
  useSymbols,
  useUpdateSymbols,
} from '@/features/symbols/api/symbols';
import { useSystemConfig, useUpdateInterval } from '@/features/system/api/systemConfig';

type GroupKey = 'Forex' | 'Metals' | 'Indices' | 'Crypto' | 'Other';

const GROUP_ORDER: GroupKey[] = ['Forex', 'Metals', 'Indices', 'Crypto', 'Other'];

const FOREX_TOKENS = ['forex', 'currenc', 'fx', 'валют', 'divisa', 'moedas'] as const;
const METALS_TOKENS = ['metal', 'metales', 'metais', 'gold', 'silver', 'oro', 'ouro', 'plata', 'prata', 'металл'] as const;
const INDICES_TOKENS = ['index', 'indices', 'indice', 'индекс'] as const;
const CRYPTO_TOKENS = ['crypto', 'cripto', 'digital', 'крипто'] as const;

function classifySymbol(symbol: BrokerSymbol): GroupKey {
  const path = (symbol.path || '').toLowerCase();
  if (FOREX_TOKENS.some((t) => path.includes(t))) return 'Forex';
  if (METALS_TOKENS.some((t) => path.includes(t))) return 'Metals';
  if (INDICES_TOKENS.some((t) => path.includes(t))) return 'Indices';
  if (CRYPTO_TOKENS.some((t) => path.includes(t))) return 'Crypto';
  return 'Other';
}

export default function SymbolsSection() {
  const { data: activeData } = useSymbols();
  const { data: brokerCatalog, isLoading: catalogLoading } = useBrokerSymbols();
  const { data: config } = useSystemConfig();
  const updateSymbols = useUpdateSymbols();
  const updateInterval = useUpdateInterval();
  const { isFree, copy, openUpgradeModal } = useTierGate();

  const [selected, setSelected] = useState<string[]>([]);
  const [search, setSearch] = useState('');
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

  const grouped = useMemo(() => {
    const symbols = brokerCatalog?.symbols ?? [];
    const needle = search.trim().toLowerCase();
    const filtered = needle
      ? symbols.filter((s) =>
          s.name.toLowerCase().includes(needle) ||
          (s.description || '').toLowerCase().includes(needle),
        )
      : symbols;

    const out: Record<GroupKey, BrokerSymbol[]> = {
      Forex: [], Metals: [], Indices: [], Crypto: [], Other: [],
    };
    for (const s of filtered) out[classifySymbol(s)].push(s);
    for (const k of GROUP_ORDER) out[k].sort((a, b) => a.name.localeCompare(b.name));
    return out;
  }, [brokerCatalog, search]);

  const limitReached = selected.length >= maxActiveSymbols;

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

  const totalCatalogCount = brokerCatalog?.symbols.length ?? 0;

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
            <Search size={14} strokeWidth={3} className="absolute left-4 top-1/2 -translate-y-1/2 text-black/20 dark:text-white/20" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={catalogLoading ? 'Loading broker catalogue…' : `Search ${totalCatalogCount} broker symbols`}
              disabled={catalogLoading}
              className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white dark:bg-black pl-11 pr-4 py-2.5 text-sm font-bold text-black dark:text-white placeholder:text-black/20 dark:placeholder:text-white/20 focus:border-brand transition-all outline-none disabled:opacity-40"
            />
          </div>

          {!catalogLoading && totalCatalogCount === 0 && (
            <div className="text-center text-[11px] font-bold text-black/30 dark:text-white/30 py-10 italic bg-black/5 dark:bg-white/5 rounded-xl border border-dashed border-black/10 dark:border-white/10">
              No broker symbols available. Connect a broker first.
            </div>
          )}

          {GROUP_ORDER.map((group) => {
            const items = grouped[group];
            if (items.length === 0) return null;
            return (
              <div key={group} className="space-y-2">
                <div className="text-[10px] font-black uppercase tracking-[0.2em] text-black/30 dark:text-white/30">{group}</div>
                <div className="grid grid-cols-2 gap-2">
                  {items.map((s) => {
                    const isSelected = selected.includes(s.name);
                    const disabledForCap = isFree && !isSelected && limitReached;
                    return (
                      <label
                        key={s.name}
                        title={disabledForCap ? gateCopy.body : s.description || s.path || s.name}
                        className={`flex items-center gap-3 text-xs p-2 rounded-lg transition-all ${
                          disabledForCap
                            ? 'cursor-not-allowed text-black/20 dark:text-white/20'
                            : 'cursor-pointer text-black/60 dark:text-white/60 font-bold hover:bg-black/5 dark:hover:bg-white/5'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          disabled={disabledForCap}
                          onChange={() => (disabledForCap ? openUpgradeModal() : toggleSymbol(s.name))}
                          className="h-4 w-4 rounded border-black/10 dark:border-white/10 text-brand focus:ring-brand disabled:opacity-20 transition-all cursor-pointer"
                        />
                        <span className="tracking-tight">{s.name}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          })}

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
