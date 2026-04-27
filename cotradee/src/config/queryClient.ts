import { QueryClient } from '@tanstack/react-query';

/**
 * Application-wide TanStack Query client.
 *
 * Defaults are tuned for a real-time trading dashboard:
 *
 *   • Server state is authoritative and the WebSocket pushes deltas,
 *     so we keep polling intervals short (3-5s) on individual queries
 *     and let the WS invalidations refresh the rest.
 *   • `refetchOnWindowFocus` is OFF: traders switch between charts,
 *     terminals and the dashboard constantly; a focus-driven storm
 *     is unhelpful and the WS keeps data fresh anyway.
 *   • `refetchOnReconnect` is ON so a flaky network reconvergence
 *     refreshes everything.
 *   • `networkMode: 'always'` keeps queries from going to the
 *     'paused' state when the browser briefly reports offline; trade
 *     panels must never blank out because of a wifi blink.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      gcTime: 5 * 60_000,
      retry: 1,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      refetchOnMount: 'always',
      networkMode: 'always',
    },
    mutations: {
      retry: 0,
      networkMode: 'always',
    },
  },
});
