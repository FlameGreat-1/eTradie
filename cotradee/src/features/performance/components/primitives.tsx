import { type ReactNode } from 'react';
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  Info,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import type {
  ConfidenceBand,
  EvolutionDirection,
  WarningSeverity,
} from '../types';

/**
 * Shared UI primitives for the Performance Review feature. Every
 * component is fully responsive (mobile / tablet / desktop), dark /
 * light aware via tailwind's dark: prefix, and accessible (semantic
 * roles, focus rings, ARIA where applicable).
 *
 * The visual language matches the existing dashboard:
 *   - Surfaces: bg-white / bg-black with 5% border for separation.
 *   - Type:     tight tracking, bold headings, modest body weight.
 *   - Tone:     calm and analytical — no gradients, no neon, no
 *               motivational decoration. This mirrors PLAN.md's
 *               'institutional / calm' tonal mandate.
 */

// ---------------------------------------------------------------------------
// ReviewCard - the surface every section sits on.
// ---------------------------------------------------------------------------

interface ReviewCardProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function ReviewCard({
  title,
  subtitle,
  icon,
  action,
  children,
  className = '',
}: ReviewCardProps) {
  return (
    <section
      className={`rounded-2xl border border-black/5 dark:border-white/5 bg-white dark:bg-black
                 shadow-sm overflow-hidden ${className}`}
    >
      <header className="flex items-start justify-between gap-4 px-5 sm:px-6 pt-5 sm:pt-6 pb-3">
        <div className="flex items-start gap-3 min-w-0">
          {icon && (
            <div
              aria-hidden
              className="shrink-0 w-9 h-9 rounded-xl bg-black/5 dark:bg-white/5
                         flex items-center justify-center text-black/70 dark:text-white/70"
            >
              {icon}
            </div>
          )}
          <div className="min-w-0">
            <h2 className="text-sm sm:text-base font-bold tracking-tight text-black dark:text-white truncate">
              {title}
            </h2>
            {subtitle && (
              <p className="mt-0.5 text-[11px] sm:text-xs font-medium text-black/50 dark:text-white/50 truncate">
                {subtitle}
              </p>
            )}
          </div>
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </header>
      <div className="px-5 sm:px-6 pb-5 sm:pb-6">{children}</div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// MetricTile - one number on the Performance Metrics grid.
// ---------------------------------------------------------------------------

interface MetricTileProps {
  label: string;
  value: string;
  tone?: 'default' | 'positive' | 'negative' | 'neutral';
}

export function MetricTile({ label, value, tone = 'default' }: MetricTileProps) {
  const display = value && value.trim() !== '' ? value : '\u2014';
  const toneClass =
    tone === 'positive'
      ? 'text-emerald-600 dark:text-emerald-400'
      : tone === 'negative'
        ? 'text-rose-600 dark:text-rose-400'
        : 'text-black dark:text-white';
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-black/5 dark:border-white/5 p-3 sm:p-4 bg-black/[0.02] dark:bg-white/[0.02]">
      <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-widest text-black/40 dark:text-white/40">
        {label}
      </span>
      <span className={`text-base sm:text-lg font-bold tracking-tight ${toneClass}`}>
        {display}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// EmptyState - rendered inside a card when the LLM had nothing to say
// for that section (e.g. low / insufficient confidence).
// ---------------------------------------------------------------------------

interface EmptyStateProps {
  message: string;
  hint?: string;
}

export function EmptyState({ message, hint }: EmptyStateProps) {
  return (
    <div
      role="note"
      className="flex flex-col items-center justify-center text-center gap-1 py-6 px-3 rounded-xl bg-black/[0.02] dark:bg-white/[0.02]"
    >
      <Sparkles size={16} className="text-black/30 dark:text-white/30" aria-hidden />
      <p className="text-xs sm:text-sm font-medium text-black/50 dark:text-white/50">{message}</p>
      {hint && (
        <p className="text-[11px] sm:text-xs text-black/40 dark:text-white/40">{hint}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ConfidenceBadge
// ---------------------------------------------------------------------------

export function ConfidenceBadge({ band, sampleSize }: { band: ConfidenceBand; sampleSize: number }) {
  const palette: Record<ConfidenceBand, { label: string; tone: string }> = {
    high: {
      label: 'High confidence',
      tone: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20',
    },
    medium: {
      label: 'Medium confidence',
      tone: 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20',
    },
    low: {
      label: 'Low confidence',
      tone: 'bg-orange-500/10 text-orange-700 dark:text-orange-300 border-orange-500/20',
    },
    insufficient: {
      label: 'Insufficient sample',
      tone: 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/20',
    },
  };
  const cfg = palette[band] ?? palette.insufficient;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] sm:text-[11px] font-bold uppercase tracking-widest ${cfg.tone}`}
    >
      <Info size={11} aria-hidden />
      <span>{cfg.label}</span>
      <span aria-hidden className="opacity-60">·</span>
      <span>{sampleSize} trades</span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// SeverityBadge
// ---------------------------------------------------------------------------

export function SeverityBadge({ severity }: { severity: WarningSeverity }) {
  const palette: Record<WarningSeverity, { label: string; tone: string; Icon: typeof Info }> = {
    info: {
      label: 'Info',
      tone: 'bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/20',
      Icon: Info,
    },
    warning: {
      label: 'Warning',
      tone: 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20',
      Icon: AlertTriangle,
    },
    critical: {
      label: 'Critical',
      tone: 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/20',
      Icon: AlertTriangle,
    },
  };
  const cfg = palette[severity] ?? palette.info;
  const { Icon } = cfg;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[10px] font-bold uppercase tracking-widest ${cfg.tone}`}
    >
      <Icon size={11} aria-hidden />
      {cfg.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// DirectionBadge
// ---------------------------------------------------------------------------

export function DirectionBadge({ direction, delta }: { direction: EvolutionDirection; delta: string }) {
  const cfg = (() => {
    switch (direction) {
      case 'improved':
        return {
          tone: 'text-emerald-600 dark:text-emerald-400',
          Icon: TrendingUp,
          label: 'Improved',
        };
      case 'declined':
        return {
          tone: 'text-rose-600 dark:text-rose-400',
          Icon: TrendingDown,
          label: 'Declined',
        };
      default:
        return {
          tone: 'text-black/50 dark:text-white/50',
          Icon: ArrowRight,
          label: 'Stable',
        };
    }
  })();
  const { Icon } = cfg;
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] sm:text-xs font-bold ${cfg.tone}`}>
      <Icon size={13} aria-hidden />
      <span>{cfg.label}</span>
      {delta && (
        <span aria-hidden className="opacity-70">
          · {delta}
        </span>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// PnLDirectionIcon - small affordance used inside MetricTile for net_pnl.
// ---------------------------------------------------------------------------

export function PnLDirectionIcon({ value }: { value: string }) {
  if (!value) return null;
  const trimmed = value.trim();
  if (trimmed.startsWith('+')) {
    return (
      <ArrowUpRight size={14} className="text-emerald-600 dark:text-emerald-400" aria-hidden />
    );
  }
  if (trimmed.startsWith('-')) {
    return (
      <ArrowDownRight size={14} className="text-rose-600 dark:text-rose-400" aria-hidden />
    );
  }
  return <CheckCircle2 size={14} className="text-black/40 dark:text-white/40" aria-hidden />;
}
