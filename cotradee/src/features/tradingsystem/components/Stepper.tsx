import { memo } from 'react';

interface Props {
  current: number;
  total: number;
  furthest: number; // user has reached at least this step; earlier ones are clickable
  labels: ReadonlyArray<string>;
  onJump: (idx: number) => void;
}

/**
 * Linear stepper with progress bar + clickable past steps. The user
 * can jump backwards to any previously-completed step but cannot
 * skip ahead (Next is the only forward affordance).
 */
function StepperInner({ current, total, furthest, labels, onJump }: Props) {
  const pct = Math.round(((current + 1) / total) * 100);
  return (
    <div className="border-b border-border bg-app px-4 py-1.5">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-content-muted">
          {labels[current]}
        </span>
        <span className="text-xs font-medium text-content tabular-nums">{pct}%</span>
      </div>
      <div className="relative h-1.5 w-full rounded-full bg-app overflow-hidden">
        <div
          className="h-full bg-brand transition-all duration-fast"
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {labels.map((label, idx) => {
          const reachable = idx <= furthest;
          const active = idx === current;
          return (
            <button
              key={label}
              type="button"
              disabled={!reachable}
              onClick={() => reachable && onJump(idx)}
              className={`rounded px-2 py-0.5 text-[11px] font-medium transition-colors focus-ring
                ${active
                  ? 'bg-brand text-white'
                  : reachable
                    ? 'bg-app text-content-secondary hover:text-content cursor-pointer'
                    : 'bg-app text-content-muted cursor-not-allowed opacity-60'}`}
              aria-current={active ? 'step' : undefined}
            >
              {idx + 1}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export const Stepper = memo(StepperInner);
