import {
  useEffect,
  useRef,
  useCallback,
  useMemo,
  memo,
  useState,
} from 'react';
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type IPriceLine,
  type Time,
  ColorType,
  CrosshairMode,
  LineStyle,
} from 'lightweight-charts';
import { useTheme } from '@/providers/ThemeProvider';
import { useChartCandles } from '@/features/chart/api/chartData';
import { useTickStream, type TickData } from '@/features/chart/hooks/useTickStream';
import { formatCurrency } from '@/utils/formatters';

/* ── Public types ────────────────────────────────────────────────── */

export interface TradeLevels {
  entry?: number;
  stopLoss?: number;
  takeProfit?: number;
  direction?: string;
}

export interface ActiveTrade {
  symbol: string;
  entryPrice: number;
  stopLoss: number;
  takeProfit: number;
  direction: string;
  profit: number;
}

export interface TradingChartProps {
  symbol: string;
  timeframe: string;
  levels?: TradeLevels | null;
  activeTrades?: ActiveTrade[];
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
 * Read a CSS custom property off the document root. We re-resolve
 * tokens whenever the theme class changes so colors track the active
 * palette without recreating the chart instance.
 */
function readThemeColors() {
  const styles = getComputedStyle(document.documentElement);
  const get = (name: string, fallback: string) =>
    (styles.getPropertyValue(name).trim() || fallback).trim();
  return {
    background:    get('--chart-bg',           '#0a0a0f'),
    textColor:     get('--chart-text',         '#9ca3af'),
    gridColor:     get('--chart-grid',         'rgba(255,255,255,0.04)'),
    borderColor:   get('--chart-border',       'rgba(255,255,255,0.08)'),
    crosshair:     get('--chart-crosshair',    'rgba(255,255,255,0.18)'),
    upColor:       get('--chart-up',           '#22c55e'),
    downColor:     get('--chart-down',         '#ef4444'),
    axisLabelBg:   get('--chart-axis-label-bg','rgba(20,20,25,0.92)'),
    axisLabelText: get('--chart-axis-label-text','#ffffff'),
    tooltipBg:     get('--chart-tooltip-bg',   '#1f2937'),
    success:       get('--success',            '#22c55e'),
    danger:        get('--danger',             '#ef4444'),
    info:          get('--info',               '#3b82f6'),
    warning:       get('--warning',            '#f59e0b'),
  };
}

function pipDistance(symbol: string, a: number, b: number): number {
  const diff = Math.abs(a - b);
  // JPY pairs use 0.01 pip, everything else uses 0.0001. This matches MT5.
  if (/JPY/i.test(symbol)) return diff * 100;
  return diff * 10000;
}

function directionTone(dir: string): 'BUY' | 'SELL' {
  return String(dir).toUpperCase() === 'BUY' || String(dir).toUpperCase() === 'LONG'
    ? 'BUY'
    : 'SELL';
}

/* ── Component ─────────────────────────────────────────────────── */

function TradingChartInner({
  symbol,
  timeframe,
  levels,
  activeTrades,
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const linesRef = useRef<IPriceLine[]>([]);
  const latestCandleRef = useRef<CandlestickData | null>(null);
  const lastDataKeyRef = useRef<string>('');
  const [latestPrice, setLatestPrice] = useState<number | null>(null);

  const { theme } = useTheme();
  const { data: candleData, isFetching } = useChartCandles(symbol, timeframe);

  /* ── 1. Create chart once ──────────────────────────────────── */
  useEffect(() => {
    if (!containerRef.current) return;
    const colors = readThemeColors();

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: colors.background },
        textColor: colors.textColor,
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: colors.gridColor },
        horzLines: { color: colors.gridColor },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: colors.crosshair,
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: colors.tooltipBg,
        },
        horzLine: {
          color: colors.crosshair,
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: colors.tooltipBg,
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
        barSpacing: 8,
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

    chartRef.current = chart;
    seriesRef.current = series;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      linesRef.current = [];
      latestCandleRef.current = null;
      lastDataKeyRef.current = '';
    };
  }, []);

  /* ── 2. Re-skin (no recreate) when theme flips ─────────────────────── */
  useEffect(() => {
    if (!chartRef.current || !seriesRef.current) return;
    const colors = readThemeColors();
    chartRef.current.applyOptions({
      layout: {
        background: { type: ColorType.Solid, color: colors.background },
        textColor: colors.textColor,
      },
      grid: {
        vertLines: { color: colors.gridColor },
        horzLines: { color: colors.gridColor },
      },
      crosshair: {
        vertLine: { color: colors.crosshair, labelBackgroundColor: colors.tooltipBg },
        horzLine: { color: colors.crosshair, labelBackgroundColor: colors.tooltipBg },
      },
      rightPriceScale: { borderColor: colors.borderColor },
      timeScale: { borderColor: colors.borderColor },
    });
    seriesRef.current.applyOptions({
      upColor: colors.upColor,
      downColor: colors.downColor,
      wickUpColor: colors.upColor,
      wickDownColor: colors.downColor,
    });
  }, [theme]);

  /* ── 3. Load historical candles when (symbol, timeframe, data) changes ── */
  useEffect(() => {
    if (!seriesRef.current || !chartRef.current) return;
    if (!candleData?.candles) return;

    const key = `${symbol}|${timeframe}|${candleData.candles.length}`;
    if (key === lastDataKeyRef.current) return; // already drawn
    lastDataKeyRef.current = key;

    // Lightweight Charts demands ascending time + unique timestamps.
    // MT5 frequently returns reverse-chronological data.
    const formatted: CandlestickData[] = candleData.candles
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
      latestCandleRef.current = unique.length > 0 ? { ...unique[unique.length - 1] } : null;
      if (unique.length > 0) {
        setLatestPrice(unique[unique.length - 1].close);
      }
      chartRef.current.timeScale().fitContent();
    } catch (err) {
      // Lightweight Charts throws on out-of-order data; we already
      // sort so this should be unreachable in practice. Logging
      // helps when the backend contract is violated.
      // eslint-disable-next-line no-console
      console.error('Chart setData failed:', err);
    }
  }, [candleData, symbol, timeframe]);

  /* ── 4. Live tick stream → update last candle in place ─────────────────── */
  const handleTick = useCallback(
    (tick: TickData) => {
      if (!seriesRef.current) return;
      if (tick.symbol && tick.symbol !== symbol) return;

      // Tick time can arrive in seconds or milliseconds.
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
        // Cross a candle boundary: open at prior close to avoid gaps.
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
      seriesRef.current.update(updated);
      setLatestPrice(price);
    },
    [symbol, timeframe],
  );

  useTickStream({ symbol, onTick: handleTick });

  /* ── 5. Single canonical "redraw all lines" pass ─────────────────────── */
  useEffect(() => {
    if (!seriesRef.current) return;
    const series = seriesRef.current;
    const colors = readThemeColors();

    // Wipe everything we've drawn and start fresh. This is O(n) where
    // n is the number of lines, typically <= 6, so it's cheaper than
    // a diff and impossible to leave stale.
    for (const line of linesRef.current) {
      try { series.removePriceLine(line); } catch { /* already gone */ }
    }
    linesRef.current = [];

    const labelStyle = {
      axisLabelColor: colors.axisLabelBg,
      axisLabelTextColor: colors.axisLabelText,
    };

    // Planned levels (only when no live trade exists for the symbol).
    if (levels && (!activeTrades || activeTrades.length === 0)) {
      if (Number.isFinite(levels.entry)) {
        linesRef.current.push(
          series.createPriceLine({
            price: levels.entry as number,
            color: colors.info,
            lineWidth: 2,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            ...labelStyle,
            title: 'Entry',
          }),
        );
      }
      if (Number.isFinite(levels.stopLoss)) {
        linesRef.current.push(
          series.createPriceLine({
            price: levels.stopLoss as number,
            color: colors.danger,
            lineWidth: 2,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            ...labelStyle,
            title: 'SL',
          }),
        );
      }
      if (Number.isFinite(levels.takeProfit)) {
        linesRef.current.push(
          series.createPriceLine({
            price: levels.takeProfit as number,
            color: colors.success,
            lineWidth: 2,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            ...labelStyle,
            title: 'TP',
          }),
        );
      }
    }

    // Active trade levels (broker truth).
    if (activeTrades && activeTrades.length > 0) {
      for (const trade of activeTrades) {
        if (trade.symbol !== symbol) continue;
        const tone = directionTone(trade.direction);
        linesRef.current.push(
          series.createPriceLine({
            price: trade.entryPrice,
            color: tone === 'BUY' ? colors.success : colors.danger,
            lineWidth: 2,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            ...labelStyle,
            title: `${tone} · Entry`,
          }),
        );
        if (trade.stopLoss > 0) {
          linesRef.current.push(
            series.createPriceLine({
              price: trade.stopLoss,
              color: colors.danger,
              lineWidth: 1,
              lineStyle: LineStyle.Dotted,
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
              lineWidth: 1,
              lineStyle: LineStyle.Dotted,
              axisLabelVisible: true,
              ...labelStyle,
              title: 'TP',
            }),
          );
        }
      }
    }
  }, [levels, activeTrades, symbol, theme]);

  /* ── 6. Live P&L overlay ─────────────────────────────────────────── */
  const overlay = useMemo(() => {
    const trade = activeTrades?.find((t) => t.symbol === symbol);
    if (!trade) return null;
    const tone = directionTone(trade.direction);
    const price = latestPrice ?? trade.entryPrice;
    const pipsToTp =
      trade.takeProfit > 0 ? pipDistance(symbol, price, trade.takeProfit) : null;
    const pipsToSl =
      trade.stopLoss > 0 ? pipDistance(symbol, price, trade.stopLoss) : null;
    return {
      tone,
      price,
      pipsToTp,
      pipsToSl,
      profit: trade.profit,
    };
  }, [activeTrades, symbol, latestPrice]);

  /* ── 7. Render ────────────────────────────────────────────────────── */
  return (
    <div className="relative w-full h-full bg-[var(--chart-bg)]">
      <div
        ref={containerRef}
        id="trading-chart-container"
        className="w-full h-full"
        style={{ minHeight: 240 }}
      />

      {/* Loading skeleton */}
      {isFetching && !candleData && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-surface-2/80 border border-border text-xs text-content-secondary">
            <span className="inline-block w-2 h-2 rounded-full bg-brand animate-pulse" />
            Loading {symbol} · {timeframe}…
          </div>
        </div>
      )}

      {/* Live P&L overlay */}
      {overlay && (
        <div
          className="absolute top-3 left-3 z-10 flex items-center gap-3 px-3 py-2
                     rounded-lg border border-border bg-surface-glass
                     shadow-card text-xs select-none"
        >
          <div className="flex flex-col">
            <span className="text-[10px] uppercase tracking-wider text-content-muted">
              {symbol}
            </span>
            <span
              className={`font-bold ${
                overlay.tone === 'BUY' ? 'text-success' : 'text-danger'
              }`}
            >
              {overlay.tone}
            </span>
          </div>
          <div className="w-px h-8 bg-border" />
          <div className="flex flex-col">
            <span className="text-[10px] uppercase tracking-wider text-content-muted">
              P&L
            </span>
            <span
              className={`font-bold ${
                overlay.profit >= 0 ? 'text-success' : 'text-danger'
              }`}
            >
              {overlay.profit >= 0 ? '+' : ''}
              {formatCurrency(overlay.profit)}
            </span>
          </div>
          {overlay.pipsToTp != null && (
            <>
              <div className="w-px h-8 bg-border" />
              <div className="flex flex-col">
                <span className="text-[10px] uppercase tracking-wider text-content-muted">
                  to TP
                </span>
                <span className="font-semibold text-success">
                  {overlay.pipsToTp.toFixed(1)} pips
                </span>
              </div>
            </>
          )}
          {overlay.pipsToSl != null && (
            <>
              <div className="w-px h-8 bg-border" />
              <div className="flex flex-col">
                <span className="text-[10px] uppercase tracking-wider text-content-muted">
                  to SL
                </span>
                <span className="font-semibold text-danger">
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
