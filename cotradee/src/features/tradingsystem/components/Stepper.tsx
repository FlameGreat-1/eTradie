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
    <div className="py-1">
      <div className="flex items-center justify-between mb-2 px-1">
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-black text-brand uppercase tracking-[0.2em]">
            Step {current + 1}
          </span>
          <span className="text-[10px] font-bold text-black/30 dark:text-white/30 uppercase tracking-widest">
            {labels[current]}
          </span>
        </div>
        <span className="text-[10px] font-black text-black/50 dark:text-white/50 tabular-nums tracking-widest">{pct}% Complete</span>
      </div>
      
      <div className="flex gap-1 h-1">
        {Array.from({ length: total }).map((_, idx) => {
          const isPast = idx < current;
          const isActive = idx === current;
          const isReachable = idx <= furthest;
          
          return (
            <button
              key={idx}
              type="button"
              disabled={!isReachable}
              onClick={() => isReachable && onJump(idx)}
              className={`flex-1 rounded-full transition-all duration-300 h-full
                ${isActive 
                  ? 'bg-brand' 
                  : isPast 
                    ? 'bg-brand/30 hover:bg-brand/50' 
                    : isReachable 
                      ? 'bg-black/10 dark:bg-white/10 hover:bg-black/20 dark:hover:border-white/20' 
                      : 'bg-black/5 dark:bg-white/5'}`}
              title={labels[idx]}
            />
          );
        })}
      </div>
    </div>
  );
}

export const Stepper = memo(StepperInner);
