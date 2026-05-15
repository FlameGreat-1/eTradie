import { useNavigate } from 'react-router-dom';
import { ArrowRight, Zap } from 'lucide-react';

/**
 * WelcomeSetupCard
 *
 * Empty-state hero shown on the dashboard for users who have no
 * broker connection.
 *
 * Design: Enterprise Pure Black/White/Nvidia.
 */
export function WelcomeSetupCard() {
  const navigate = useNavigate();

  return (
    <div className="flex h-full w-full items-center justify-center px-4 py-8 bg-black">
      <div className="w-full max-w-lg rounded-3xl border border-white/10 bg-white/[0.03] p-8 sm:p-12 text-center shadow-2xl">
        {/* Brand accent */}
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand/10 border border-brand/20">
          <Zap className="h-8 w-8 text-brand" />
        </div>

        <h2 className="text-2xl font-bold text-white tracking-tight">Welcome to Exoper</h2>
        <p className="mt-3 text-sm text-white/50 leading-relaxed max-w-sm mx-auto">
          Setup and configure your account to start trading. It only
          takes a few minutes, and you can revisit any step later.
        </p>

        <div className="mx-auto mt-8 max-w-xs space-y-3 text-left">
          {[
            'Connect your MT4 or MT5 broker',
            'Pick your trading symbols',
            'Build your personal operating system',
          ].map((point) => (
            <div key={point} className="flex items-start gap-3">
              <div className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success/15">
                <svg className="h-3 w-3 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <span className="text-sm text-white/70">{point}</span>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => navigate('/onboarding')}
          className="mt-10 w-full rounded-2xl bg-white px-6 py-4 text-sm font-bold text-black shadow-xl
                     hover:bg-white/90 active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2"
        >
          Get started <ArrowRight size={18} />
        </button>

        <p className="mt-5 text-[11px] text-white/20">
          You can also configure everything later from <span className="text-white/40">Settings</span>.
        </p>
      </div>
    </div>
  );
}
