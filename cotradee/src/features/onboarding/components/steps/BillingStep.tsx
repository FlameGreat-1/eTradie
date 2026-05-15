import { useAuth } from '@/features/auth';
import { useTierGate } from '@/features/auth/hooks/useTierGate';
import { Check, ChevronRight, CreditCard, Sparkles, Zap } from 'lucide-react';

interface Props { onComplete: () => void; }

export function BillingStep({ onComplete }: Props) {
  const { user } = useAuth();
  const { isFree, tier } = useTierGate();
  
  const tierName = tier.split('_').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(' ');

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="text-center mb-8">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5 border border-white/10">
          <CreditCard className="h-6 w-6 text-content" />
        </div>
        <h2 className="text-xl font-bold text-content">Billing & Plan</h2>
        <p className="mt-2 text-sm text-content-secondary">
          Your account is currently on the {tierName} plan.
        </p>
      </div>

      <div className={`rounded-2xl border p-6 space-y-6 ${!isFree ? 'border-brand/30 bg-brand/5' : 'border-white/10 bg-white/5'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${!isFree ? 'bg-brand/20' : 'bg-white/10'}`}>
              {!isFree ? <Sparkles className="h-5 w-5 text-brand" /> : <Zap className="h-5 w-5 text-white/40" />}
            </div>
            <div>
              <p className="text-sm font-bold text-content">{tierName}</p>
              <p className="text-[11px] text-content-secondary uppercase tracking-widest font-medium">Active Status</p>
            </div>
          </div>
          <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
        </div>

        <ul className="space-y-3">
          {[
            'Real-time Market Analysis',
            'Automated Trade Execution',
            isFree ? '1 Active Symbol' : 'Unlimited Symbols',
            !isFree ? 'Enterprise AI Models' : 'Standard AI Models'
          ].map((feat, i) => (
            <li key={i} className="flex items-center gap-2.5 text-xs text-content-secondary font-medium">
              <Check size={12} className="text-success" />
              {feat}
            </li>
          ))}
        </ul>

        <button
          onClick={onComplete}
          className="w-full rounded-xl bg-white p-3.5 text-sm font-bold text-black hover:bg-white/90 transition-all flex items-center justify-center gap-2"
        >
          Continue with {tierName} <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
