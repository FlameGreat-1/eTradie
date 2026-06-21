import { memo, useState, useEffect, useCallback, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import Sidebar from './Sidebar';
import Header from './Header';
import { ErrorBoundary } from '@/components/error/ErrorBoundary';
import { useLiveReasoningStream } from '@/features/alerts/hooks/useLiveReasoningStream';
import { AnalysisOverlay } from '@/features/chart/components/AnalysisOverlay';
import { useActiveBrokerConnection } from '@/features/broker/api/brokerConnections';
import { WelcomeBuilderModal } from '@/features/tradingsystem/components/WelcomeBuilderModal';

interface Props {
  children: ReactNode;
}

function DashboardLayout({ children }: Props) {
  const queryClient = useQueryClient();
  const location = useLocation();
  const [isOverlayVisible, setOverlayVisible] = useState(false);
  const [isMobileNavOpen, setMobileNavOpen] = useState(false);

  const onDashboard = location.pathname === '/dashboard';

  const broker = useActiveBrokerConnection();
  const stream = useLiveReasoningStream(() => {
    void queryClient.invalidateQueries({ queryKey: ['analysis'] });
  });

  useEffect(() => {
    if (stream.isStreaming || stream.analysisId) {
      setOverlayVisible(true);
    }
  }, [stream.isStreaming, stream.analysisId]);

  const handleMenuClick = useCallback(() => setMobileNavOpen(true), []);
  const handleMenuClose = useCallback(() => setMobileNavOpen(false), []);

  return (
    <div className="relative min-h-[100dvh] flex flex-col bg-app text-content select-none">
      <Sidebar
        isMobileOpen={isMobileNavOpen}
        onMobileClose={handleMenuClose}
      />
      <Header onMenuClick={handleMenuClick} />

      <main
        className="relative flex-1 bg-app"
        style={{
          marginLeft: 'var(--main-left, 0px)',
          paddingTop: 'var(--header-height)',
        }}
      >
        <style>{`
          @media (min-width: 768px) {
            :root { --main-left: var(--sidebar-width); }
          }
          @media (max-width: 767.98px) {
            :root { --main-left: 0px; }
          }
        `}</style>
        <ErrorBoundary>
          {children}
        </ErrorBoundary>

        {/* PRACTICE.md first-login popup: shown once when the user's
            trading system status is 'none'. Mounts at the layout
            level (not the page level) so it appears regardless of
            which dashboard sub-route the user lands on after signup.
            Suppressed automatically once status becomes 'active' or
            'skipped' (server-side source of truth, no localStorage). */}
        {/* Suppress the Step 3 nudge popup while the user is looking at
            the 7-step master WelcomeSetupCard on the dashboard. */}
        {!(onDashboard && !broker.isLoading && !broker.data) && (
          <WelcomeBuilderModal />
        )}

        {/* Live reasoning overlay — only on the dashboard route.
            `dismissed_analysis_id` is a UI preference (see
            docs/cookie-auth.md): it stops the same completed
            analysis from popping back up after the user has read
            it. No credential is stored under this key. */}
        {onDashboard && isOverlayVisible && (
          <AnalysisOverlay
            stream={stream}
            onDismiss={() => {
              if (stream.analysisId) {
                localStorage.setItem('dismissed_analysis_id', stream.analysisId);
              }
              setOverlayVisible(false);
            }}
          />
        )}
      </main>
    </div>
  );
}

export default memo(DashboardLayout);
