import { useState, useEffect } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { useAuth } from '@/features/auth/context/AuthContext';

/**
 * Fetch historical OHLCV candles for the dashboard chart.
 *
 * Returns data in TradingView Lightweight Charts format:
 *   { time: number, open, high, low, close, volume }[]
 *
 * Performance contract
 * --------------------
 *   * placeholderData: keepPreviousData
 *       The previous symbol/timeframe's candles remain visible while a
 *       new fetch is in flight. The chart never blanks during a switch.
 *   * staleTime: 30s
 *       Matches the server-side SWR revalidation window so the client
 *       does not trigger a refetch the server would have served from
 *       its own warm cache anyway.
 *   * gcTime: 10m
 *       Keeps recently-viewed (symbol, timeframe) pairs in memory so
 *       toggling between them is an instant cache read with no network.
 *   * retry policy
 *       The server returns HTTP 504 when its own cold-fetch deadline
 *       is exceeded. That is a transient "warming up" signal -- exactly
 *       the case where a single retry has very high success probability
 *       because the in-flight refresh will have populated Redis. We
 *       therefore retry once on 504/502/503 with a short backoff and do
 *       not retry on 4xx client errors.
 *
 * Automatically refetches when symbol or timeframe changes.
 */
export interface ChartCandle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChartCandlesResponse {
  symbol: string;
  timeframe: string;
  candles: ChartCandle[];
}

export function useChartCandles(symbol: string, timeframe: string) {
  const { isAuthenticated } = useAuth();
  const [requestedCount, setRequestedCount] = useState(500);

  // Reset count to 500 whenever symbol or timeframe changes to ensure
  // the next view also starts with an instant cache hit from the pre-warm.
  useEffect(() => {
    setRequestedCount(500);
  }, [symbol, timeframe]);

  return useQuery<ChartCandlesResponse>({
    // Include requestedCount in queryKey so the second stage triggers a new fetch.
    queryKey: ['chart', 'candles', symbol, timeframe, requestedCount],
    queryFn: async () => {
      const { data } = await api.engine.get<ChartCandlesResponse>(
        '/api/broker/candles',
        { params: { symbol, timeframe, count: requestedCount } },
      );

      // 3-Stage Progressive Upgrade Path:
      // Stage 1 (500) -> Stage 2 (1000) -> Stage 3 (2000)
      if (requestedCount === 500) {
        setTimeout(() => setRequestedCount(1000), 100);
      } else if (requestedCount === 1000) {
        setTimeout(() => setRequestedCount(2000), 100);
      }

      return data;
    },
    enabled: !!symbol && isAuthenticated,
    staleTime: 30_000,
    gcTime: 10 * 60_000,
    refetchOnWindowFocus: false,
    // CRITICAL: keepPreviousData ensures the 500 candles stay visible 
    // while the 2000-candle request is in flight.
    placeholderData: keepPreviousData,
    retry: (failureCount, error: unknown) => {
      const status = (error as { response?: { status?: number } })?.response
        ?.status;
      if (status && status >= 400 && status < 500 && status !== 408) {
        return false;
      }
      return failureCount < 2;
    },
    retryDelay: (attempt) => Math.min(1500 * 2 ** attempt, 6000),
  });
}
