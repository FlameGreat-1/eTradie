import { memo, useState, useEffect, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import Sidebar from './Sidebar';
import Header from './Header';
import { SIDEBAR_WIDTH, HEADER_HEIGHT } from '@/utils/constants';
import { useLiveReasoningStream } from '@/features/alerts/hooks/useLiveReasoningStream';
import { AnalysisOverlay } from '@/features/chart/components/AnalysisOverlay';

interface Props {
  children: ReactNode;
}

function DashboardLayout({ children }: Props) {
  const queryClient = useQueryClient();
  const [isOverlayVisible, setOverlayVisible] = useState(false);

  // Global live reasoning stream. Triggers across all pages.
  const stream = useLiveReasoningStream(() => {
    void queryClient.invalidateQueries({ queryKey: ['analysis'] });
  });

  // Auto-show overlay when a new stream starts or a new analysis is hydrated from the DB
  useEffect(() => {
    if (stream.isStreaming || stream.analysisId) {
      setOverlayVisible(true);
    }
  }, [stream.isStreaming, stream.analysisId]);

  return (
    <div className="fixed inset-0 w-screen h-screen overflow-hidden bg-surface-0">
      <Sidebar />
      <Header />
      <main
        className="absolute overflow-auto bg-surface-0"
        style={{
          left: SIDEBAR_WIDTH,
          top: HEADER_HEIGHT,
          right: 0,
          bottom: 0,
        }}
      >
        {children}
        
        {/* Global Analysis overlay — floats on top of everything */}
        {isOverlayVisible && (
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
