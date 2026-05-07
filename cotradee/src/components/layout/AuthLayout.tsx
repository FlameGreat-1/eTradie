import type { ReactNode } from 'react';
import ParticlesCanvas from '@/features/landing/components/ParticlesCanvas';
import '@/features/landing/landing.css';

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="landing-page min-h-screen flex items-center justify-center text-white px-4 py-8">
      {/* Neural network particle background */}
      <ParticlesCanvas />

      {/* Content above particles */}
      <div className="relative z-10 w-full max-w-md">{children}</div>
    </div>
  );
}
