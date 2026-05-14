import { type HTMLAttributes } from 'react';

interface Props extends HTMLAttributes<HTMLDivElement> {
  size?: number;
}

/**
 * Shared Exoper loading logo with the signature zoom in/out animation.
 * Used across the dashboard, onboarding, and standalone pages to 
 * maintain visual consistency and avoid duplication.
 */
export function LogoLoader({ size = 48, className = '', ...props }: Props) {
  return (
    <div 
      className={`flex flex-col items-center justify-center pointer-events-none gap-3 ${className}`}
      {...props}
    >
      <img 
        src="/assets/sidebar/icons/logo.svg" 
        alt="Loading" 
        style={{ 
          width: size, 
          height: size,
          animation: 'logoZoom 1.2s ease-in-out infinite' 
        }}
      />
      <style>{`
        @keyframes logoZoom {
          0%, 100% { transform: scale(0.9); opacity: 0.7; }
          50% { transform: scale(1.15); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
