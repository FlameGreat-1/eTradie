import {
  useEffect,
  useRef,
  useCallback,
  memo,
} from 'react';
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
  ColorType,
  CrosshairMode,
  LineStyle,
} from 'lightweight-charts';
import { useTheme } from '@/providers/ThemeProvider';
import { useChartCandles } from '@/features/chart/api/chartData';
import { useTickStream, type TickData } from '@/features/chart/hooks/useTickStream';

/* ── Theme color palettes ─────────────────────────────────── */

const DARK_THEME = {
  background: '#0a0a0f',
  textColor: '#9ca3af',
  gridColor: 'rgba(255,255,255,0.03)',
  borderColor: 'rgba(255,255,255,0.06)',
  crosshairColor: 'rgba(255,255,255,0.15)',
  upColor: '#22c55e',
  downColor: '#ef4444',
  upWickColor: '#22c55e',
  downWickColor: '#ef4444',
};

const LIGHT_THEME = {
  background: '#ffffff',
  textColor: '#374151',
  gridColor: 'rgba(0,0,0,0.04)',
  borderColor: 'rgba(0,0,0,0.08)',
  crosshairColor: 'rgba(0,0,0,0.15)',
  upColor: '#16a34a',
  downColor: '#dc2626',
  upWickColor: '#16a34a',
  downWickColor: '#dc2626',
};

/* ── Level colors ─────────────────────────────────────────── */

const LEVEL_COLORS = {
  entry: 'rgba(59, 130, 246, 0.4)',      // Blue (subtle)
  stopLoss: 'rgba(239, 68, 68, 0.4)',   // Red (subtle)
  takeProfit: 'rgba(34, 197, 94, 0.4)', // Green (subtle)
  trade: 'rgba(245, 158, 11, 0.4)',      // Amber (subtle)
};

// Faint label style: dark background matching chart, white text.
const AXIS_LABEL_STYLE = {
  axisLabelColor: 'rgba(20, 20, 25, 0.85)',
  axisLabelTextColor: '#ffffff',
};

/* ── Props ────────────────────────────────────────────────── */

interface TradeLevels {
  entry?: number;
  stopLoss?: number;
  takeProfit?: number;
  direction?: string;
}

interface ActiveTrade {
  symbol: string;
  entryPrice: number;
  stopLoss: number;
  takeProfit: number;
  direction: string;
  profit: number;
}

interface TradingChartProps {
  symbol: string;
  timeframe: string;
  levels?: TradeLevels | null;
  activeTrades?: ActiveTrade[];
}

/* ── Component ────────────────────────────────────────────── */

function TradingChartInner({
  symbol,
  timeframe,
  levels,
  activeTrades,
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const levelLinesRef = useRef<any[]>([]);
  const latestCandleRef = useRef<CandlestickData | null>(null);
  const { theme } = useTheme();

  const colors = theme === 'dark' ? DARK_THEME : LIGHT_THEME;

  // Fetch historical candles.
  const { data: candleData } = useChartCandles(symbol, timeframe);

  // Live tick stream callback — updates the last candle in real-time.
  const handleTick = useCallback((tick: TickData) => {
    if (!seriesRef.current || tick.symbol !== symbol) return;

    // Use tick timestamp if available, fallback to Date.now()
    let nowSec = Math.floor(Date.now() / 1000);
    if (tick.time) {
       nowSec = tick.time > 1e11 ? Math.floor(tick.time / 1000) : Math.floor(tick.time);
    }

    // Round to the current candle period boundary.
    const periodSeconds = timeframeToPeriod(timeframe);
    const candleTime = Math.floor(nowSec / periodSeconds) * periodSeconds;
    const price = (tick.bid + tick.ask) / 2;

    const currentCandle = latestCandleRef.current;
    let updatedCandle: CandlestickData;

    if (currentCandle && currentCandle.time === candleTime) {
      // Update existing candle
      updatedCandle = {
        time: candleTime as Time,
        open: currentCandle.open,
        high: Math.max(currentCandle.high, price),
        low: Math.min(currentCandle.low, price),
        close: price,
      };
    } else {
      // Create new candle (time crossed boundary)
      updatedCandle = {
        time: candleTime as Time,
        open: currentCandle ? currentCandle.close : price, // gap prevention
        high: currentCandle ? Math.max(currentCandle.close, price) : price,
        low: currentCandle ? Math.min(currentCandle.close, price) : price,
        close: price,
      };
    }

    latestCandleRef.current = updatedCandle;
    seriesRef.current.update(updatedCandle);
  }, [symbol, timeframe]);

  useTickStream({ symbol, onTick: handleTick });

  // Create/destroy chart on mount/unmount.
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.background },
        textColor: colors.textColor,
        fontFamily: "'Inter', 'SF Pro Display', -apple-system, sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: colors.gridColor },
        horzLines: { color: colors.gridColor },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: colors.crosshairColor,
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: theme === 'dark' ? '#1f2937' : '#e5e7eb',
        },
        horzLine: {
          color: colors.crosshairColor,
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: theme === 'dark' ? '#1f2937' : '#e5e7eb',
        },
      },
      rightPriceScale: {
        borderColor: colors.borderColor,
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: colors.borderColor,
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 12,
        barSpacing: 8,
        minBarSpacing: 2,
      },
      handleScroll: { vertTouchDrag: false },
    });

    const series = chart.addCandlestickSeries({
      upColor: colors.upColor,
      downColor: colors.downColor,
      borderVisible: false,
      wickUpColor: colors.upWickColor,
      wickDownColor: colors.downWickColor,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    // Resize observer for responsive layout.
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        chart.applyOptions({ width, height });
      }
    });
    ro.observe(containerRef.current);
    resizeObserverRef.current = ro;

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  // Re-create chart when theme changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);

  // Load historical data when it arrives or symbol/timeframe changes.
  useEffect(() => {
    if (!seriesRef.current || !candleData?.candles) return;

    const formatted: CandlestickData[] = candleData.candles.map((c) => ({
      time: c.time as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    // Lightweight Charts strictly requires chronological order and unique timestamps.
    // MT5 often returns history in reverse-chronological order.
    const sorted = formatted.sort((a, b) => (a.time as number) - (b.time as number));
    
    const unique: CandlestickData[] = [];
    const seen = new Set<number>();
    for (const c of sorted) {
      const t = c.time as number;
      if (!seen.has(t)) {
        seen.add(t);
        unique.push(c);
      }
    }

    try {
      seriesRef.current.setData(unique);
      if (unique.length > 0) {
        latestCandleRef.current = { ...unique[unique.length - 1] };
      } else {
        latestCandleRef.current = null;
      }
    } catch (err) {
      console.error('Failed to set chart data:', err);
    }

    // Fit content with a small right margin for live candle space.
    chartRef.current?.timeScale().fitContent();
  }, [candleData]);

  // Draw analysis levels (Entry, SL, TP).
  useEffect(() => {
    if (!seriesRef.current) return;

    // Remove old level lines.
    for (const line of levelLinesRef.current) {
      try {
        seriesRef.current.removePriceLine(line);
      } catch { /* already removed */ }
    }
    levelLinesRef.current = [];

    if (!levels) return;

    if (levels.entry != null) {
      const line = seriesRef.current.createPriceLine({
        price: levels.entry,
        color: LEVEL_COLORS.entry,
        lineWidth: 2,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        ...AXIS_LABEL_STYLE,
        title: `Entry`,
      });
      levelLinesRef.current.push(line);
    }

    if (levels.stopLoss != null) {
      const line = seriesRef.current.createPriceLine({
        price: levels.stopLoss,
        color: LEVEL_COLORS.stopLoss,
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        ...AXIS_LABEL_STYLE,
        title: `SL`,
      });
      levelLinesRef.current.push(line);
    }

    if (levels.takeProfit != null) {
      const line = seriesRef.current.createPriceLine({
        price: levels.takeProfit,
        color: LEVEL_COLORS.takeProfit,
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        ...AXIS_LABEL_STYLE,
        title: `TP`,
      });
      levelLinesRef.current.push(line);
    }
  }, [levels]);

  // Draw active trade levels.
  useEffect(() => {
    if (!seriesRef.current || !activeTrades?.length) return;

    // Active trade levels are drawn alongside analysis levels,
    // managed through the same levelLinesRef so they get cleaned up properly.
    for (const trade of activeTrades) {
      if (trade.symbol !== symbol) continue;

      const entryLine = seriesRef.current.createPriceLine({
        price: trade.entryPrice,
        color: LEVEL_COLORS.trade,
        lineWidth: 1,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        ...AXIS_LABEL_STYLE,
        title: `${trade.direction} Entry`,
      });
      levelLinesRef.current.push(entryLine);

      if (trade.stopLoss > 0) {
        const slLine = seriesRef.current.createPriceLine({
          price: trade.stopLoss,
          color: LEVEL_COLORS.stopLoss,
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          axisLabelVisible: true,
          ...AXIS_LABEL_STYLE,
          title: `Trade SL`,
        });
        levelLinesRef.current.push(slLine);
      }

      if (trade.takeProfit > 0) {
        const tpLine = seriesRef.current.createPriceLine({
          price: trade.takeProfit,
          color: LEVEL_COLORS.takeProfit,
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          axisLabelVisible: true,
          ...AXIS_LABEL_STYLE,
          title: `Trade TP`,
        });
        levelLinesRef.current.push(tpLine);
      }
    }
  }, [activeTrades, symbol]);

  return (
    <div
      ref={containerRef}
      id="trading-chart-container"
      className="w-full h-full"
      style={{ minHeight: 400 }}
    />
  );
}

/* ── Helpers ──────────────────────────────────────────────── */

function timeframeToPeriod(tf: string): number {
  const map: Record<string, number> = {
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
  };
  return map[tf] || 3600;
}

export const TradingChart = memo(TradingChartInner);
export type { TradeLevels, ActiveTrade, TradingChartProps };
