import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { queryClient } from '@/config/queryClient';
import { AuthProvider } from '@/features/auth';
import { RealtimeProvider } from '@/features/realtime';
import { ConsentProvider } from '@/features/consent/ConsentContext';
import ConsentAuthBridge from '@/features/consent/ConsentAuthBridge';
import { ThemeProvider } from './ThemeProvider';
import type { ReactNode } from 'react';

/**
 * Application-level provider stack.
 *
 * Order matters:
 *  1. BrowserRouter   → routing primitives
 *  2. QueryClient     → server-state cache (must wrap Realtime so it
 *                       can call invalidateQueries)
 *  3. ThemeProvider   → token + class binding on <html>
 *  4. AuthProvider    → session state (must wrap Realtime so the
 *                       socket only opens when authenticated; must
 *                       also wrap Consent so the attach-on-login
 *                       bridge can subscribe to auth state)
 *  5. ConsentProvider → cookie-consent state. Mounted inside Auth so
 *                       its ConsentAuthBridge can read useAuth().
 *  6. RealtimeProvider→ single WS that drives instant invalidations
 *                       across all panels.
 */
export function AppProvider({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter
      future={{
        v7_relativeSplatPath: true,
        v7_startTransition: true,
      }}
    >
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthProvider>
            <ConsentProvider>
              <ConsentAuthBridge />
              <RealtimeProvider>{children}</RealtimeProvider>
            </ConsentProvider>
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </BrowserRouter>
  );
}
