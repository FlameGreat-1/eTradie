import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'monospace'],
      },
      colors: {
        brand: {
          DEFAULT: 'var(--brand)',
          hover: 'var(--brand-hover)',
          active: 'var(--brand-active)',
          soft: 'var(--brand-soft)',
          'soft-strong': 'var(--brand-soft-strong)',
          /* Aliases preserved for backward compatibility with existing markup */
          dark: 'var(--brand-active)',
          light: 'var(--brand-hover)',
        },
        surface: {
          0: 'var(--surface-0)',
          1: 'var(--surface-1)',
          2: 'var(--surface-2)',
          3: 'var(--surface-3)',
          elevated: 'var(--surface-elevated)',
          glass: 'var(--surface-glass)',
        },
        border: {
          DEFAULT: 'var(--border)',
          strong: 'var(--border-strong)',
          subtle: 'var(--border-subtle)',
        },
        content: {
          DEFAULT: 'var(--content)',
          secondary: 'var(--content-secondary)',
          muted: 'var(--content-muted)',
          faint: 'var(--content-faint)',
        },
        success: {
          DEFAULT: 'var(--success)',
          soft: 'var(--success-soft)',
        },
        danger: {
          DEFAULT: 'var(--danger)',
          soft: 'var(--danger-soft)',
        },
        warning: {
          DEFAULT: 'var(--warning)',
          soft: 'var(--warning-soft)',
        },
        info: {
          DEFAULT: 'var(--info)',
          soft: 'var(--info-soft)',
        },
      },
      spacing: {
        sidebar: 'var(--sidebar-width)',
        header: 'var(--header-height)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
      },
      zIndex: {
        sidebar: 'var(--z-sidebar)',
        header: 'var(--z-header)',
        dropdown: 'var(--z-dropdown)',
        modal: 'var(--z-modal)',
        toast: 'var(--z-toast)',
        overlay: 'var(--z-overlay)',
      },
      boxShadow: {
        card: 'var(--shadow-sm)',
        pop: 'var(--shadow-md)',
        modal: 'var(--shadow-lg)',
        glow: 'var(--brand-glow)',
        dropdown: 'var(--shadow-md)',
      },
      transitionTimingFunction: {
        'out-expo': 'var(--ease-out)',
        'in-out-expo': 'var(--ease-in-out)',
      },
      transitionDuration: {
        fast: 'var(--duration-fast)',
        base: 'var(--duration-base)',
        slow: 'var(--duration-slow)',
      },
      animation: {
        'fade-in': 'fadeIn var(--duration-base, 180ms) var(--ease-out, ease-out)',
        'slide-up': 'slideUp var(--duration-slow, 280ms) var(--ease-out, ease-out)',
        'slide-right': 'slideRight var(--duration-slow, 280ms) var(--ease-out, ease-out)',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideRight: {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
