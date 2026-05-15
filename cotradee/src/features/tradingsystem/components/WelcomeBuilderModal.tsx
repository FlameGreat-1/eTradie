import { useEffect, useState } from 'react';
import { BuilderModal } from '@/features/tradingsystem/components/BuilderModal';
import { useTradingSystemStatus } from '@/features/tradingsystem/api/hooks';
import { ArrowRight, Cpu } from 'lucide-react';

/**
 * WelcomeBuilderModal
 *
 * Enterprise design: Pure Black/White/Nvidia.
 */
export function WelcomeBuilderModal() {
  const { data: statusData, isLoading } = useTradingSystemStatus();
  const [builderOpen, setBuilderOpen] = useState(false);
  const [welcomeVisible, setWelcomeVisible] = useState(false);

  useEffect(() => {
    if (isLoading) return;
    if (sessionStorage.getItem('exoper_welcome_dismissed') === 'true') return;
    if (statusData?.status === 'none') {
      setWelcomeVisible(true);
    }
  }, [isLoading, statusData?.status]);

  function handleStartBuilder() {
    setWelcomeVisible(false);
    setBuilderOpen(true);
  }

  function handleMaybeLater() {
    sessionStorage.setItem('exoper_welcome_dismissed', 'true');
    setWelcomeVisible(false);
  }

  function handleBuilderClose() {
    setBuilderOpen(false);
  }

  if (!welcomeVisible && !builderOpen) return null;

  return (
    <>
      {welcomeVisible && (
        <div
          className="fixed inset-0 z-modal flex items-center justify-center bg-black/60 backdrop-blur-md px-4"
          role="dialog"
          aria-modal="true"
        >
          <div className="relative w-full max-w-md rounded-3xl border border-border bg-surface-1 p-10 shadow-2xl text-center">
            {/* Brand accent */}
            <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand/10 border border-brand/20 overflow-hidden">
              <img src="/assets/sidebar/icons/logo.svg" alt="Exoper" className="h-8 w-8" />
            </div>

            <h2 className="text-2xl font-bold text-content tracking-tight">Build Your Trading System</h2>
            <p className="mt-3 text-sm text-content-secondary leading-relaxed max-w-sm mx-auto">
              Spare 2&ndash;3 minutes to configure your personal trading
              identity. This personalises every Exoper analysis to your exact approach.
            </p>

            <div className="mx-auto mt-8 max-w-xs space-y-3 text-left">
              {[
                'Tailored analysis to your trading style',
                'Risk guardrails that match your goals',
                'Execution preferences respected globally',
              ].map((point) => (
                <div key={point} className="flex items-start gap-3">
                  <div className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success/15">
                    <svg className="h-3 w-3 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span className="text-sm text-content-secondary">{point}</span>
                </div>
              ))}
            </div>

            <div className="mt-10 flex flex-col gap-3">
              <button
                type="button"
                onClick={handleStartBuilder}
                className="w-full rounded-2xl bg-black dark:bg-white px-6 py-4 text-sm font-bold text-white dark:text-black shadow-xl
                           hover:opacity-90 active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2"
              >
                Start the builder <ArrowRight size={18} />
              </button>
              <button
                type="button"
                onClick={handleMaybeLater}
                className="w-full rounded-2xl border border-border bg-surface-2 px-6 py-4 text-sm font-semibold
                           text-content-muted hover:text-content hover:border-border-strong transition-all duration-200"
              >
                Maybe later
              </button>
            </div>
          </div>
        </div>
      )}

      <BuilderModal
        open={builderOpen}
        onClose={handleBuilderClose}
        onComplete={handleBuilderClose}
      />
    </>
  );
}
