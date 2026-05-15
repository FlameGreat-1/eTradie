import { useState } from 'react';
import { useTradingSystemStatus } from '@/features/tradingsystem/api/hooks';
import { BuilderModal } from '@/features/tradingsystem/components/BuilderModal';
import { Check, Cpu } from 'lucide-react';

interface Props { onComplete: () => void; }

export function TradingSystemStep({ onComplete }: Props) {
  const { data: statusData } = useTradingSystemStatus();
  const [builderOpen, setBuilderOpen] = useState(false);
  const isDone = statusData?.status === 'active';

  if (isDone) {
    return (
      <div className="flex flex-col items-center gap-6 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-success/10"><Check className="h-8 w-8 text-success" /></div>
        <h2 className="text-xl font-bold text-content">Trading system active</h2>
        <button onClick={onComplete} className="inline-flex items-center gap-2 rounded-xl bg-black dark:bg-white px-6 py-3 text-sm font-semibold text-white dark:text-black hover:opacity-90">Continue</button>
      </div>
    );
  }

  return (
    <>
      <div className="w-full max-w-md mx-auto text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-2 border border-border"><Cpu className="h-6 w-6 text-content" /></div>
        <h2 className="text-xl font-bold text-content">Build your trading system</h2>
        <button onClick={() => setBuilderOpen(true)} className="mt-8 w-full rounded-xl bg-black dark:bg-white p-3 font-bold text-white dark:text-black hover:opacity-90 transition-all">Start the builder</button>
      </div>
      <BuilderModal open={builderOpen} onClose={() => setBuilderOpen(false)} onComplete={() => { setBuilderOpen(false); onComplete(); }} />
    </>
  );
}
