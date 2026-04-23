import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';

/**
 * Fetch historical OHLCV candles for the dashboard chart.
 *
 * Returns data in TradingView Lightweight Charts format:
 *   { time: number, open, high, low, close, volume }[]
 *
 * Automatically refetches when symbol or timeframe changes.
 */
export function useChartCandles(symbol: string, timeframe: string) {
  return useQuery({
    queryKey: ['chart', 'candles', symbol, timeframe],
    queryFn: async () => {
      const { data } = await api.engine.get<{
        symbol: string;
        timeframe: string;
        candles: Array<{
          time: number;
          open: number;
          high: number;
          low: number;
          close: number;
          volume: number;
        }>;
      }>('/api/broker/candles', {
        params: { symbol, timeframe, count: 500 },
      });
      return data;
    },
    enabled: !!symbol,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}
