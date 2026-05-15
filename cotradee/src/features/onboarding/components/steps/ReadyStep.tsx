import { useNavigate } from 'react-router-dom';
import { useOnboardingProgress } from '@/features/tradingsystem/hooks/useOnboardingProgress';
import { ArrowRight, Sparkles } from 'lucide-react';

export function ReadyStep() {
  const navigate = useNavigate();
  const { perStep } = useOnboardingProgress();

  return (
    <div className="w-full max-w-md mx-auto text-center">
      <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-brand/10 border border-brand/20"><Sparkles className="h-9 w-9 text-brand" /></div>
      <h2 className="text-2xl font-bold text-content">You're all set</h2>
      <button onClick={() => navigate('/dashboard', { replace: true })} className="mt-8 w-full rounded-xl bg-white p-4 font-bold text-black flex items-center justify-center gap-2">Go to Dashboard <ArrowRight size={16} /></button>
    </div>
  );
}
