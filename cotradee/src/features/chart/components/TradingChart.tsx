import {
  useEffect,
  useRef,
  useCallback,
  useMemo,
  memo,
  useState,
} from 'react';
import type {
  IChartApi,
  ISeriesApi,
  CandlestickData,
  IPriceLine,
  Time,
} from 'lightweight-charts';
import { AlertTriangle } from 'lucide-react';
import { useChartCandles } from '@/features/chart/api/chartData';
import { useTickStream, type TickData } from '@/features/chart/hooks/useTickStream';
import { formatCurrency } from '@/utils/formatters';

/**
 * lightweight-charts is loaded via dynamic import() to prevent its
 * internal navigator.userAgentData.brands.some() probe from crashing
 * at module-eval time on mobile browsers where the polyfill fails.
 */
type LWCModule = typeof import('lightweight-charts');

/* ── Public types ────────────────────────────────────────────────── */

export interface ActiveTrade {
  symbol: string;
  entryPrice: number;
  stopLoss: number;
  takeProfit: number;
  direction: string;
  profit: number;
  isPending?: boolean;
}

export interface TradingChartProps {
  symbol: string;
  timeframe: string;
  activeTrades?: ActiveTrade[];
  symbolMeta?: Record<string, { point: number; digits: number }>;
}

/* ── Helpers ───────────────────────────────────────────────────── */

const TF_PERIOD_SECONDS: Record<string, number> = {
  M1: 60,
  M5: 300,
  M15: 900,
  M30: 1800,
  H1: 3600,
  H3: 10800,
  H4: 14400,
  H6: 21600,
  H8: 28800,
  H12: 43200,
  D1: 86400,
  W1: 604800,
  MN1: 2592000,
};

function periodSeconds(tf: string): number {
  return TF_PERIOD_SECONDS[tf] ?? 3600;
}

/**
 * Translate modern CSS color syntax into the legacy comma-separated
 * form lightweight-charts' built-in colorStringToRgba parser supports.
 */
function toLibColor(value: string): string {
  const v = value.trim();
  if (!v) return v;
  if (v.startsWith('#') || v.startsWith('rgba(')) return v;
  const m = v.match(/^rgba?\(\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)(?:\s*\/\s*([0-9.]+%?))?\s*\)$/i);
  if (m) {
    const [, r, g, b, a] = m;
    if (a != null) {
      const alpha = a.endsWith('%') ? Number(a.slice(0, -1)) / 100 : Number(a);
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    return `rgb(${r}, ${g}, ${b})`;
  }
  if (/^rgb\(\s*\d+\s*,/.test(v)) return v;
  return v;
}

function readThemeColors() {
  const styles = getComputedStyle(document.documentElement);
  const get = (name: string, fallback: string) =>
    toLibColor((styles.getPropertyValue(name).trim() || fallback).trim());
  return {
    background: get('--chart-bg', '#0a0a0f'),
    textColor: get('--chart-text', '#9ca3af'),
    gridColor: get('--chart-grid', 'rgba(255,255,255,0.04)'),
    borderColor: get('--chart-border', 'rgba(255,255,255,0.08)'),
    crosshair: get('--chart-crosshair', 'rgba(255,255,255,0.18)'),
    upColor: get('--chart-up', '#22c55e'),
    downColor: get('--chart-down', '#ef4444'),
    axisLabelBg: get('--chart-axis-label-bg', 'rgba(20,20,25,0.92)'),
    axisLabelText: get('--chart-axis-label-text', '#ffffff'),
    tooltipBg: get('--chart-tooltip-bg', '#1f2937'),
    success: get('--success', '#22c55e'),
    danger: get('--danger', '#ef4444'),
    info: get('--info', '#3b82f6'),
    warning: get('--warning', '#f59e0b'),
  };
}

function pipDistance(
  symbol: string,
  a: number,
  b: number,
  symbolMeta?: Record<string, { point: number; digits: number }>,
): number {
  const diff = Math.abs(a - b);
  const upper = symbol.toUpperCase();

  // For Deriv Synthetics, professional traders ALWAYS treat 1 full index point (1.0) as 1 "pip".
  // If we divide by the broker's raw point (e.g. 0.0001 for Crash), it displays millions of pips.
  if (/VOLATILITY|V75|V10|V25|V50|V100|BOOM|CRASH|STEP|JUMP|RANGE|DEX/i.test(upper)) {
    return diff;
  }

  // For other instruments, use broker-sourced point value if available.
  const meta = symbolMeta?.[symbol];
  if (meta && meta.point > 0) {
    return diff / meta.point;
  }

  // Fallback heuristic if no broker data is loaded yet.
  if (/JPY/i.test(upper)) return diff * 100;
  if (/^X(AU|AG|PT|PD)/.test(upper)) return diff * 100;
  if (/BTC|ETH|LTC|XRP|SOL/i.test(upper)) return diff;
  if (/US30|NAS|SPX|GER|UK/i.test(upper)) return diff;
  return diff * 10000;
}

function directionTone(dir: string): 'BUY' | 'SELL' {
  const u = String(dir).toUpperCase();
  return u === 'BUY' || u === 'LONG' ? 'BUY' : 'SELL';
}

/* ── Component ─────────────────────────────────────────────────── */

function TradingChartInner({
  symbol,
  timeframe,
  activeTrades,
  symbolMeta,
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const lwcRef = useRef<LWCModule | null>(null);
  const linesRef = useRef<IPriceLine[]>([]);
  const latestCandleRef = useRef<CandlestickData | null>(null);
  const lastDataKeyRef = useRef<string>('');
  const [latestPrice, setLatestPrice] = useState<number | null>(null);
  const [chartFailed, setChartFailed] = useState(false);
  const [chartReady, setChartReady] = useState(false);
  const [themeTick, setThemeTick] = useState(0);

  const [overlayPos, setOverlayPos] = useState({ x: 12, y: 12 });
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef({ startX: 0, startY: 0, initX: 0, initY: 0 });
  const { data: candleData } = useChartCandles(symbol, timeframe);

  const applyPalette = useCallback(() => {
    const chart = chartRef.current;
    const series = seriesRef.current;
    const lwc = lwcRef.current;
    if (!chart || !series || !lwc) return;
    const colors = readThemeColors();
    try {
      chart.applyOptions({
        layout: {
          background: { type: lwc.ColorType.Solid, color: colors.background },
          textColor: colors.textColor,
        },
        grid: {
          vertLines: { color: colors.gridColor },
          horzLines: { color: colors.gridColor },
        },
        crosshair: {
          vertLine: { color: colors.crosshair, labelBackgroundColor: colors.axisLabelBg },
          horzLine: { color: colors.crosshair, labelBackgroundColor: colors.axisLabelBg },
        },
        rightPriceScale: { borderColor: colors.borderColor },
        timeScale: { borderColor: colors.borderColor },
      });
      series.applyOptions({
        upColor: colors.upColor,
        downColor: colors.downColor,
        wickUpColor: colors.upColor,
        wickDownColor: colors.downColor,
      });
    } catch {
      /* ignore palette apply errors — chart stays on previous theme */
    }
  }, []);

  /* 1. Dynamically import lightweight-charts and create chart.
        The dynamic import() ensures the library's internal
        navigator.userAgentData.brands.some() probe runs inside
        async code we can catch, not at module-eval time. */
  useEffect(() => {
    if (!containerRef.current) return;
    let cancelled = false;
    let chart: IChartApi | null = null;

    (async () => {
      try {
        const lwc = await import('lightweight-charts');
        if (cancelled) return;
        lwcRef.current = lwc;

        const colors = readThemeColors();
        chart = lwc.createChart(containerRef.current!, {
          autoSize: true,
          layout: {
            background: { type: lwc.ColorType.Solid, color: colors.background },
            textColor: colors.textColor,
            fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
            fontSize: 11,
          },
          grid: {
            vertLines: { color: colors.gridColor },
            horzLines: { color: colors.gridColor },
          },
          crosshair: {
            mode: lwc.CrosshairMode.Normal,
            vertLine: {
              color: colors.crosshair,
              width: 1,
              style: lwc.LineStyle.Solid,
              labelBackgroundColor: colors.axisLabelBg,
            },
            horzLine: {
              color: colors.crosshair,
              width: 1,
              style: lwc.LineStyle.Solid,
              labelBackgroundColor: colors.axisLabelBg,
            },
          },
          rightPriceScale: {
            borderColor: colors.borderColor,
            scaleMargins: { top: 0.08, bottom: 0.08 },
          },
          timeScale: {
            borderColor: colors.borderColor,
            timeVisible: true,
            secondsVisible: false,
            rightOffset: 12,
            barSpacing: 4,
            minBarSpacing: 1,
          },
          handleScroll: { vertTouchDrag: false },
        });

        const series = chart.addCandlestickSeries({
          upColor: colors.upColor,
          downColor: colors.downColor,
          borderVisible: false,
          wickUpColor: colors.upColor,
          wickDownColor: colors.downColor,
        });

        if (cancelled) {
          try { chart.remove(); } catch { /* noop */ }
          return;
        }

        chartRef.current = chart;
        seriesRef.current = series;
        setChartReady(true);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('Chart library load / construction failed:', err);
        try { chart?.remove(); } catch { /* noop */ }
        if (!cancelled) setChartFailed(true);
      }
    })();

    return () => {
      cancelled = true;
      try { chartRef.current?.remove(); } catch { /* noop */ }
      chartRef.current = null;
      seriesRef.current = null;
      lwcRef.current = null;
      linesRef.current = [];
      latestCandleRef.current = null;
      lastDataKeyRef.current = '';
    };
  }, []);

  /* 2. MutationObserver → instant theme repaint. */
  useEffect(() => {
    const root = document.documentElement;
    let lastClass = root.className;
    const observer = new MutationObserver(() => {
      if (root.className === lastClass) return;
      lastClass = root.className;
      requestAnimationFrame(() => {
        applyPalette();
        setThemeTick((t) => t + 1);
      });
    });
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, [applyPalette]);

  /* 2b. Dynamic price precision configuration from symbol metadata. */
  useEffect(() => {
    if (!seriesRef.current || !chartReady) return;
    const meta = symbolMeta?.[symbol];
    
    const upper = symbol.toUpperCase();
    let precision = 5;
    if (meta && meta.digits > 0) {
      precision = meta.digits;
    } else if (upper.includes('JPY') || /^X(AU|AG|PT|PD)/.test(upper) || /US30|NAS|SPX|GER|UK/i.test(upper)) {
      precision = 2;
    } else if (/VOLATILITY|V75|V10|V25|V50|V100|BOOM|CRASH|STEP|JUMP|RANGE|DEX/i.test(upper)) {
      precision = meta?.digits ?? 2;
    }

    const minMove = meta?.point ?? (precision === 2 ? 0.01 : 0.00001);

    try {
      seriesRef.current.applyOptions({
        priceFormat: {
          type: 'price',
          precision: precision,
          minMove: minMove,
        },
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('Failed to apply priceFormat to chart series:', err);
    }
  }, [symbol, symbolMeta, chartReady]);

  /* 3. Load historical candles.
     With React-Query's keepPreviousData (see useChartCandles) the
     `candleData` prop will briefly point at the previous symbol /
     timeframe's payload while the new fetch is in flight. We must
     therefore key the redraw on (candleData.symbol, candleData.timeframe,
     candleData.candles.length, last-bar-time) and ONLY redraw when the
     payload truly matches the currently selected (symbol, timeframe).
     Crucially we never call setData([]) just because the user switched
     instruments -- that would blank the chart and reintroduce the very
     UX regression this commit set out to fix. The previous candles stay
     on screen until the new ones are ready, exactly like TradingView. */
  useEffect(() => {
    if (!seriesRef.current || !chartRef.current) return;
    if (!candleData?.candles) return;
    if (candleData.symbol !== symbol || candleData.timeframe !== timeframe) {
      // Stale payload from the previous selection; ignore. The new
      // request is already in flight and will land in a subsequent run.
      return;
    }

    const candles = candleData.candles;
    const lastTime = candles.length > 0 ? candles[candles.length - 1].time : 0;
    const key = `${symbol}|${timeframe}|${candles.length}|${lastTime}`;
    if (key === lastDataKeyRef.current) return;
    lastDataKeyRef.current = key;

    const formatted: CandlestickData[] = candles
      .map((c) => ({
        time: c.time as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
      .sort((a, b) => (a.time as number) - (b.time as number));

    const unique: CandlestickData[] = [];
    const seen = new Set<number>();
    for (const c of formatted) {
      const t = c.time as number;
      if (!seen.has(t)) {
        seen.add(t);
        unique.push(c);
      }
    }

    try {
      seriesRef.current.setData(unique);
      latestCandleRef.current =
        unique.length > 0 ? { ...unique[unique.length - 1] } : null;
      if (unique.length > 0) setLatestPrice(unique[unique.length - 1].close);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('Chart setData failed:', err);
    }
  }, [candleData, symbol, timeframe, chartReady]);

  /* 4. Live tick stream. */
  const handleTick = useCallback(
    (tick: TickData) => {
      if (!seriesRef.current || !latestCandleRef.current) return;
      if (tick.symbol && tick.symbol !== symbol) return;

      const tNow =
        typeof tick.time === 'number' && tick.time > 0
          ? tick.time > 1e11
            ? Math.floor(tick.time / 1000)
            : Math.floor(tick.time)
          : Math.floor(Date.now() / 1000);

      const period = periodSeconds(timeframe);
      const candleTime = Math.floor(tNow / period) * period;
      const price = (tick.bid + tick.ask) / 2;
      if (!Number.isFinite(price)) return;

      const last = latestCandleRef.current;
      let updated: CandlestickData;
      if (last && (last.time as number) === candleTime) {
        updated = {
          time: candleTime as Time,
          open: last.open,
          high: Math.max(last.high, price),
          low: Math.min(last.low, price),
          close: price,
        };
      } else {
        const openPrice = last ? last.close : price;
        updated = {
          time: candleTime as Time,
          open: openPrice,
          high: Math.max(openPrice, price),
          low: Math.min(openPrice, price),
          close: price,
        };
      }

      latestCandleRef.current = updated;
      try {
        seriesRef.current.update(updated);
      } catch {
        /* ignore one bad frame */
      }
      setLatestPrice(price);
    },
    [symbol, timeframe],
  );

  useTickStream({ symbol, onTick: handleTick });

  /* 5. Single canonical "redraw all lines" pass. */
  useEffect(() => {
    if (!seriesRef.current || !lwcRef.current) return;
    const series = seriesRef.current;
    const lwc = lwcRef.current;
    const colors = readThemeColors();

    for (const line of linesRef.current) {
      try { series.removePriceLine(line); } catch { /* already gone */ }
    }
    linesRef.current = [];

    const labelStyle = {
      axisLabelColor: colors.axisLabelBg,
      axisLabelTextColor: colors.axisLabelText,
    };

    try {

      if (activeTrades && activeTrades.length > 0) {
        for (const trade of activeTrades) {
          if (trade.symbol !== symbol) continue;
          const tone = directionTone(trade.direction);
          linesRef.current.push(
            series.createPriceLine({
              price: trade.entryPrice,
              color: trade.isPending ? colors.info : (tone === 'BUY' ? colors.success : colors.danger),
              lineWidth: 2,
              lineStyle: trade.isPending ? lwc.LineStyle.Dashed : lwc.LineStyle.Solid,
              axisLabelVisible: true,
              ...labelStyle,
              title: trade.isPending ? 'Pending · Entry' : `${tone} · Entry`,
            }),
          );
          if (trade.stopLoss > 0) {
            linesRef.current.push(
              series.createPriceLine({
                price: trade.stopLoss,
                color: colors.danger,
                lineWidth: trade.isPending ? 2 : 1,
                lineStyle: trade.isPending ? lwc.LineStyle.Dashed : lwc.LineStyle.Dotted,
                axisLabelVisible: true,
                ...labelStyle,
                title: 'SL',
              }),
            );
          }
          if (trade.takeProfit > 0) {
            linesRef.current.push(
              series.createPriceLine({
                price: trade.takeProfit,
                color: colors.success,
                lineWidth: trade.isPending ? 2 : 1,
                lineStyle: trade.isPending ? lwc.LineStyle.Dashed : lwc.LineStyle.Dotted,
                axisLabelVisible: true,
                ...labelStyle,
                title: 'TP',
              }),
            );
          }
        }
      }
    } catch {
      /* never let a price-line draw call crash the page */
    }
  }, [activeTrades, symbol, themeTick, chartReady]);


  /* 6. Live P&L overlay state. */
  const overlay = useMemo(() => {
    const trade = activeTrades?.find((t) => t.symbol === symbol && !t.isPending);
    if (!trade) return null;
    const tone = directionTone(trade.direction);
    const price = latestPrice ?? trade.entryPrice;
    const pipsToTp =
      trade.takeProfit > 0 ? pipDistance(symbol, price, trade.takeProfit, symbolMeta) : null;
    const pipsToSl =
      trade.stopLoss > 0 ? pipDistance(symbol, price, trade.stopLoss, symbolMeta) : null;
    return { tone, price, pipsToTp, pipsToSl, profit: trade.profit };
  }, [activeTrades, symbol, latestPrice, symbolMeta]);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (e.button !== 0 && e.pointerType === 'mouse') return;
    setIsDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initX: overlayPos.x,
      initY: overlayPos.y,
    };
  }, [overlayPos]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    setOverlayPos({
      x: dragRef.current.initX + dx,
      y: dragRef.current.initY + dy,
    });
  }, [isDragging]);

  const handlePointerUp = useCallback((e: React.PointerEvent) => {
    setIsDragging(false);
    e.currentTarget.releasePointerCapture(e.pointerId);
  }, []);

  /* 7. Render. */
  if (chartFailed) {
    return (
      <div className="relative w-full h-full bg-[var(--chart-bg)] flex items-center justify-center px-6">
        <div className="max-w-sm text-center flex flex-col items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-danger-soft text-danger">
            <AlertTriangle size={18} />
          </div>
          <h3 className="text-sm font-bold text-content">Chart unavailable</h3>
          <p className="text-xs text-content-muted">
            Your browser doesn&apos;t support the chart engine. The rest of the
            dashboard — trades, journal, account stats — keeps working
            normally. Use a recent Chrome, Edge, Safari, or Firefox to enable
            charting.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-[var(--chart-bg)]">
      <div
        ref={containerRef}
        id="trading-chart-container"
        className="w-full h-full"
        style={{ minHeight: 240 }}
      />



      {overlay && (
        <div
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          className={`absolute top-0 left-0 z-10 flex items-center gap-3 px-3 py-2
                     rounded-2xl border border-border bg-white dark:bg-black
                     shadow-pop text-xs select-none ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
          style={{ transform: `translate(${overlayPos.x}px, ${overlayPos.y}px)` }}
        >
          <div className="flex flex-col">
            <span className="text-[10px] font-bold text-content-muted">
              {symbol}
            </span>
            <span
              className={`font-black ${overlay.tone === 'BUY' ? 'text-success' : 'text-danger'
                }`}
            >
              {overlay.tone}
            </span>
          </div>
          <div className="w-px h-8 bg-border" />
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] font-bold text-content-muted">
              P&amp;L
            </span>
            <span
              className={`font-black ${overlay.profit >= 0 ? 'text-success' : 'text-danger'
                }`}
            >
              {overlay.profit >= 0 ? '+' : ''}
              {formatCurrency(overlay.profit)}
            </span>
          </div>
          {overlay.pipsToTp != null && (
            <>
              <div className="w-px h-8 bg-border" />
              <div className="flex flex-col gap-0.5">
                <span className="text-[10px] font-bold text-content-muted">
                  To TP
                </span>
                <span className="font-black text-success">
                  {overlay.pipsToTp.toFixed(1)} pips
                </span>
              </div>
            </>
          )}
          {overlay.pipsToSl != null && (
            <>
              <div className="w-px h-8 bg-border" />
              <div className="flex flex-col gap-0.5">
                <span className="text-[10px] font-bold text-content-muted">
                  To SL
                </span>
                <span className="font-black text-danger">
                  {overlay.pipsToSl.toFixed(1)} pips
                </span>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export const TradingChart = memo(TradingChartInner);