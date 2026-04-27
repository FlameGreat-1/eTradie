import type { ReactNode } from 'react';

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div
      className="min-h-screen flex items-center justify-center bg-app text-content px-4 py-8"
      style={{
        backgroundImage:
          'radial-gradient(circle at 20% 0%, var(--brand-soft) 0%, transparent 40%),\n           radial-gradient(circle at 80% 100%, var(--brand-soft) 0%, transparent 40%)',
      }}
    >
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
