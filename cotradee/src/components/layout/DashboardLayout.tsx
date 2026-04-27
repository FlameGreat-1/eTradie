import { memo, useState, useEffect, useCallback, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import Sidebar from './Sidebar';
import Header from './Header';
import { ErrorBoundary } from '@/components/error/ErrorBoundary';
import { useLiveReasoningStream } from '@/features/alerts/hooks/useLiveReasoningStream';
import { AnalysisOverlay } from '@/features/chart/components/AnalysisOverlay';

interface Props {
  children: ReactNode;
}

function DashboardLayout({ children }: Props) {
  const queryClient = useQueryClient();
  const location = useLocation();
  const [isOverlayVisible, setOverlayVisible] = useState(false);
  const [isMobileNavOpen, setMobileNavOpen] = useState(false);

  const onDashboard = location.pathname === '/';

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
    <div className="fixed inset-0 w-screen h-screen overflow-hidden bg-app text-content">
      <Sidebar
        isMobileOpen={isMobileNavOpen}
        onMobileClose={handleMenuClose}
      />
      <Header onMenuClick={handleMenuClick} />

      <main
        className="absolute overflow-auto bg-app"
        style={{
          left: 'var(--main-left, 0px)',
          top: 'var(--header-height)',
          right: 0,
          bottom: 0,
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

        {/* Live reasoning overlay — only on the dashboard route. */}
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
