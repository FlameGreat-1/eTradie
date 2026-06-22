import { useEffect, useMemo, useRef, useState } from 'react';
import { Search, ChevronRight, AlertCircle, Loader2 } from 'lucide-react';
import {
  useBrokerRegistry,
  type BrandRecord,
} from '@/features/broker/api/brokerRegistry';

interface Props {
  onSelect: (brand: BrandRecord) => void;
  onAdvanced?: () => void;
  initialBrandId?: string;
}

export function FindBrokerStep({ onSelect, onAdvanced, initialBrandId }: Props) {
  const { data: brands, isLoading, isError, error, refetch } = useBrokerRegistry();

  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const listRef = useRef<HTMLUListElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const filtered = useMemo<BrandRecord[]>(() => {
    const list = brands ?? [];
    const q = query.trim().toLowerCase();
    if (!q) {
      return [...list].sort((a, b) => a.display_name.localeCompare(b.display_name));
    }
    return list
      .filter(
        (b) =>
          b.display_name.toLowerCase().includes(q) ||
          b.brand_id.toLowerCase().includes(q),
      )
      .sort((a, b) => a.display_name.localeCompare(b.display_name));
  }, [brands, query]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query, brands]);

  useEffect(() => {
    const el = listRef.current?.children[activeIndex] as HTMLElement | undefined;
    el?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!initialBrandId || !brands?.length) return;
    const match = brands.find((b) => b.brand_id === initialBrandId);
    if (match) setQuery(match.display_name);
  }, [initialBrandId, brands]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (filtered.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(filtered.length - 1, i + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(0, i - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const brand = filtered[activeIndex];
      if (brand) onSelect(brand);
    } else if (e.key === 'Escape') {
      setQuery('');
    }
  };

  return (
    <div className="w-full max-w-md mx-auto px-4 sm:px-6">
      <div className="text-center mb-8">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-2 border border-border">
          <Search className="h-6 w-6 text-content" />
        </div>
        <h2 className="text-xl font-bold text-content">Find your broker</h2>
        <p className="mt-2 text-sm text-content-secondary">
          Start typing your broker&apos;s name. We&apos;ll handle the rest.
        </p>
      </div>

      <div className="space-y-3">
        <label className="block">
          <span className="text-[10px] text-content-muted uppercase font-bold tracking-wider">
            Broker name
          </span>
          <div className="relative mt-1">
            <Search
              size={14}
              strokeWidth={2.5}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-content-faint"
            />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g. Deriv, Exness…"
              autoComplete="off"
              autoCorrect="off"
              spellCheck={false}
              className="w-full rounded-lg border border-border bg-surface-2 pl-9 pr-3 py-2.5 text-sm text-content placeholder:text-content-faint focus:outline-none focus:border-brand transition-colors"
            />
          </div>
        </label>

        <div className="rounded-lg border border-border bg-surface-2 overflow-hidden">
          {isLoading && (
            <div className="flex items-center justify-center gap-2 py-8 text-xs text-content-muted">
              <Loader2 size={14} className="animate-spin" />
              Loading broker catalog…
            </div>
          )}

          {!isLoading && isError && (
            <div className="flex flex-col items-center justify-center gap-3 py-8 px-4 text-center">
              <AlertCircle className="h-5 w-5 text-danger" />
              <p className="text-xs text-content-muted">
                Could not load the broker catalog.
                {error instanceof Error ? ` ${error.message}` : ''}
              </p>
              <button
                type="button"
                onClick={() => refetch()}
                className="text-xs font-semibold text-brand hover:opacity-80"
              >
                Try again
              </button>
            </div>
          )}

          {!isLoading && !isError && filtered.length === 0 && (
            <div className="py-8 px-4 text-center">
              <p className="text-xs text-content-muted">
                No supported broker matches &ldquo;{query}&rdquo;.
              </p>
              {onAdvanced && (
                <button
                  type="button"
                  onClick={onAdvanced}
                  className="mt-3 text-xs font-semibold text-brand hover:opacity-80"
                >
                  Use advanced setup →
                </button>
              )}
            </div>
          )}

          {!isLoading && !isError && filtered.length > 0 && (
            <ul
              ref={listRef}
              role="listbox"
              aria-label="Broker results"
              className="max-h-72 overflow-y-auto divide-y divide-border"
            >
              {filtered.map((brand, idx) => {
                const isActive = idx === activeIndex;
                return (
                  <li key={brand.brand_id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={isActive}
                      onMouseEnter={() => setActiveIndex(idx)}
                      onClick={() => onSelect(brand)}
                      className={`w-full flex items-center justify-between gap-3 px-3 py-2.5 text-left transition-colors
                        ${isActive ? 'bg-brand/10' : 'hover:bg-surface-3'}`}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-content">
                          <HighlightedMatch text={brand.display_name} query={query} />
                        </div>
                        <div className="mt-0.5 text-[11px] text-content-muted truncate">
                          {brand.entities.length === 1
                            ? brand.entities[0].display_name
                            : `${brand.entities.length} legal entities`}
                          {brand.mt5_supported && (
                            <span className="ml-2 inline-flex items-center rounded bg-surface-3 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-content-muted">
                              MT5
                            </span>
                          )}
                          {brand.mt4_supported && (
                            <span className="ml-1 inline-flex items-center rounded bg-surface-3 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-content-muted">
                              MT4
                            </span>
                          )}
                        </div>
                      </div>
                      <ChevronRight
                        size={14}
                        className={`shrink-0 ${isActive ? 'text-brand' : 'text-content-faint'}`}
                      />
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {onAdvanced && !isLoading && !isError && filtered.length > 0 && (
          <div className="text-center pt-2">
            <button
              type="button"
              onClick={onAdvanced}
              className="text-[11px] font-medium text-content-muted hover:text-content underline-offset-2 hover:underline"
            >
              Can&apos;t find your broker? Use advanced setup →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function HighlightedMatch({ text, query }: { text: string; query: string }) {
  const q = query.trim();
  if (!q) return <>{text}</>;
  const lower = text.toLowerCase();
  const idx = lower.indexOf(q.toLowerCase());
  if (idx === -1) return <>{text}</>;
  return (
    <>
      {text.slice(0, idx)}
      <span className="text-brand font-bold">{text.slice(idx, idx + q.length)}</span>
      {text.slice(idx + q.length)}
    </>
  );
}
