import type { ReactNode } from 'react';
import BeamGridBackground from '@/features/landing/components/beam-grid-background';
import LandingHeader from '@/features/landing/components/LandingHeader';
import '@/features/landing/landing.css';
import { useTheme } from '@/providers/ThemeProvider';

export default function AuthLayout({ children }: { children: ReactNode }) {
  const { theme } = useTheme();

  return (
    <div className="landing-page min-h-screen flex flex-col-reverse md:flex-row relative overflow-hidden transition-colors duration-500"
         style={{ background: 'var(--landing-bg)', color: 'var(--landing-text)' }}>
      <LandingHeader />

      {/* ── Left Side (Bottom on Mobile): Marketing Content ──────────────────── */}
      <div className="flex flex-1 relative flex-col justify-between p-8 md:p-12 lg:p-16 border-t md:border-t-0 md:border-r"
           style={{ borderColor: 'var(--landing-header-border)' }}>
        <div className="absolute inset-0 h-[500px] md:h-full overflow-hidden">
          <BeamGridBackground />
        </div>
        
        <div className="relative z-10 mt-12 md:mt-32 max-w-lg">
          <p className="text-[#76B900] font-mono text-[10px] md:text-sm mb-4 md:mb-6 tracking-widest">$ exoper analyze --live</p>
          <h1 className="text-3xl lg:text-5xl font-bold mb-4 md:mb-6 leading-[1.1] tracking-tight">
            Institutional AI.<br />
            Personal Edge.
          </h1>
          <p className="text-base lg:text-lg leading-relaxed" style={{ opacity: 0.68 }}>
            Connect your broker and let our AI handle the precision. 
            Automated execution, real-time risk management, and institutional analytics.
          </p>
        </div>

        <div className="relative z-10 flex gap-4 md:gap-8 text-[9px] md:text-[10px] font-bold tracking-widest uppercase opacity-60 mt-12 md:mt-0">
          <span>AI-DRIVEN</span>
          <span>•</span>
          <span>99.9% Uptime</span>
          <span>•</span>
          <span>Secure</span>
        </div>
      </div>

      {/* ── Right Side (Top on Mobile): Auth Form ─────────────────────────── */}
      <div className="flex-1 flex items-center justify-center p-6 pt-24 md:p-12 relative z-10 min-h-[550px] md:min-h-0"
           style={{ background: 'var(--landing-bg)' }}>
        <div className="w-full max-w-[420px]">
          {children}
        </div>
      </div>
    </div>
  );
}
