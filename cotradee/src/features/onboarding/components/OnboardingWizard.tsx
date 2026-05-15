import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOnboardingProgress } from '@/features/tradingsystem/hooks/useOnboardingProgress';
import { ProgressRing } from './ProgressRing';
import { BrokerStep } from './steps/BrokerStep';
import { SymbolsStep } from './steps/SymbolsStep';
import { TradingSystemStep } from './steps/TradingSystemStep';
import { BillingStep } from './steps/BillingStep';
import { ApiKeyStep } from './steps/ApiKeyStep';
import { ExecutionStep } from './steps/ExecutionStep';
import { ReadyStep } from './steps/ReadyStep';
import { ArrowLeft } from 'lucide-react';

const TOTAL_STEPS = 7;

export function OnboardingWizard() {
  const navigate = useNavigate();
  const { perStep, loading } = useOnboardingProgress();
  const [current, setCurrent] = useState(0);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (loading || mounted) return;
    setMounted(true);
    const doneFlags = [perStep.broker, perStep.symbols, perStep.tradingSystem, true, perStep.llm, perStep.execution, perStep.ready];
    const firstIncomplete = doneFlags.findIndex(d => !d);
    if (firstIncomplete >= 0) setCurrent(firstIncomplete);
    else setCurrent(TOTAL_STEPS - 1);
  }, [loading, mounted, perStep]);

  const advance = useCallback(() => setCurrent(c => Math.min(c + 1, TOTAL_STEPS - 1)), []);
  const goBack = useCallback(() => setCurrent(c => Math.max(0, c - 1)), []);
  const handleSkip = useCallback(() => { sessionStorage.setItem('exoper_onboarding_skipped', 'true'); navigate('/dashboard', { replace: true }); }, [navigate]);

  const stepComponent = useMemo(() => {
    switch (current) {
      case 0: return <BrokerStep onComplete={advance} />;
      case 1: return <SymbolsStep onComplete={advance} />;
      case 2: return <TradingSystemStep onComplete={advance} />;
      case 3: return <BillingStep onComplete={advance} />;
      case 4: return <ApiKeyStep onComplete={advance} />;
      case 5: return <ExecutionStep onComplete={advance} />;
      case 6: return <ReadyStep />;
      default: return null;
    }
  }, [current, advance]);

  if (loading) return <div className="flex h-64 items-center justify-center"><div className="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-white" /></div>;

  return (
    <div className="relative w-full max-w-4xl mx-auto min-h-[500px] flex flex-col bg-surface-1 text-content rounded-3xl border border-border overflow-hidden shadow-2xl">
      <header className="flex items-center justify-between px-6 py-5 border-b border-border shrink-0">
        <div className="flex items-center gap-2.5">
          <span className="text-sm font-bold tracking-tight text-content uppercase tracking-widest opacity-90">Setup Wizard</span>
        </div>
        <div className="flex items-center gap-4">
          <ProgressRing current={current} total={TOTAL_STEPS} size={38} />
          {current < TOTAL_STEPS - 1 && (
            <button onClick={handleSkip} className="text-xs font-medium text-content-muted hover:text-content transition-colors uppercase tracking-widest">
              Skip
            </button>
          )}
        </div>
      </header>
      <main className="flex-1 min-h-0 overflow-y-auto">
        <div className="flex min-h-full items-center justify-center px-6 py-12">
          <div key={current} className="w-full max-w-xl animate-in fade-in slide-in-from-bottom-2 duration-300">{stepComponent}</div>
        </div>
      </main>
      {current > 0 && current < TOTAL_STEPS - 1 && (
        <footer className="flex items-center justify-between px-6 py-4 border-t border-border shrink-0">
          <button onClick={goBack} className="inline-flex items-center gap-1.5 text-xs font-medium text-content-muted hover:text-content"><ArrowLeft size={14} /> Back</button>
          <div className="text-[11px] text-content-faint">Step {current + 1} of {TOTAL_STEPS}</div>
        </footer>
      )}
    </div>
  );
}
