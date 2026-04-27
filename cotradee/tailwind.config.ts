import type { Config } from 'tailwindcss';

/**
 * The colour palette is published as RGB triplets in CSS so Tailwind's
 * `<alpha-value>` modifier (e.g. `bg-brand/20`) compiles to a valid
 * `rgb(r g b / 0.2)` rule in both themes.
 *
 * Where a colour does not have an `-rgb` triplet (e.g. `*-soft` already
 * encodes its own opacity), it is declared as a direct CSS variable.
 */
function rgb(token: string) {
  return `rgb(var(${token}) / <alpha-value>)`;
}

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
          DEFAULT: rgb('--brand-rgb'),
          hover: rgb('--brand-hover-rgb'),
          active: rgb('--brand-active-rgb'),
          soft: 'var(--brand-soft)',
          'soft-strong': 'var(--brand-soft-strong)',
          dark: rgb('--brand-active-rgb'),
          light: rgb('--brand-hover-rgb'),
        },
        surface: {
          0: rgb('--surface-0-rgb'),
          1: rgb('--surface-1-rgb'),
          2: rgb('--surface-2-rgb'),
          3: rgb('--surface-3-rgb'),
          elevated: rgb('--surface-elevated-rgb'),
          glass: 'var(--surface-glass)',
        },
        border: {
          DEFAULT: rgb('--border-rgb'),
          strong: rgb('--border-strong-rgb'),
          subtle: rgb('--border-subtle-rgb'),
        },
        content: {
          DEFAULT: rgb('--content-rgb'),
          secondary: rgb('--content-secondary-rgb'),
          muted: rgb('--content-muted-rgb'),
          faint: rgb('--content-faint-rgb'),
        },
        success: {
          DEFAULT: rgb('--success-rgb'),
          soft: 'var(--success-soft)',
        },
        danger: {
          DEFAULT: rgb('--danger-rgb'),
          soft: 'var(--danger-soft)',
        },
        warning: {
          DEFAULT: rgb('--warning-rgb'),
          soft: 'var(--warning-soft)',
        },
        info: {
          DEFAULT: rgb('--info-rgb'),
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
