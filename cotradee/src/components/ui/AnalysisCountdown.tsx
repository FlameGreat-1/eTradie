import { useState, useEffect, useMemo } from 'react';
import { Clock, Zap } from 'lucide-react';
import { useUsage } from '@/hooks/useUsage';

/**
 * AnalysisCountdown — shown to Free tier users.
 *
 * Displays a live countdown timer until their next analysis is available
 * (24 hours after last_analysis_at). When the timer expires the button
 * lights up indicating they can run another analysis.
 */
export default function AnalysisCountdown() {
  const { data: usage, isLoading } = useUsage();
  const [now, setNow] = useState(() => Date.now());

  // Tick every second for a live countdown.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const isFree = usage?.tier === 'free';
  const dailyLimit = usage?.daily_limit;

  const analysesToday = usage?.analyses_today ?? 0;
  const lastAnalysisAt = usage?.last_analysis_at;
  const hasUsedToday = dailyLimit != null && analysesToday >= dailyLimit;

  // Calculate time until next available analysis (24h after last_analysis_at).
  const remaining = useMemo(() => {
    if (!lastAnalysisAt || !hasUsedToday) return null;

    const lastMs = new Date(lastAnalysisAt).getTime();
    const nextAvailableMs = lastMs + 24 * 60 * 60 * 1000;
    const diff = nextAvailableMs - now;
    return diff > 0 ? diff : 0;
  }, [lastAnalysisAt, hasUsedToday, now]);

  // If not free tier or no limit, don't render anything.
  if (!isFree || dailyLimit == null) return null;

  if (isLoading) return null;

  // Format remaining time as HH:MM:SS.
  const formatTime = (ms: number) => {
    const totalSec = Math.floor(ms / 1000);
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Analysis is available!
  if (!hasUsedToday || remaining === 0 || remaining === null) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-success/30 bg-success/5 px-3 py-2">
        <Zap size={14} className="text-success" />
        <span className="text-xs font-semibold text-success">
          Analysis available
        </span>
        <span className="text-[10px] text-content-muted ml-auto">
          {analysesToday}/{dailyLimit} used today
        </span>
      </div>
    );
  }

  // Countdown active — user must wait.
  return (
    <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/5 px-3 py-2">
      <Clock size={14} className="text-danger animate-pulse" />
      <div className="flex-1">
        <span className="text-xs font-semibold text-danger">
          Next analysis in{' '}
          <span className="font-mono tabular-nums">{formatTime(remaining)}</span>
        </span>
        <span className="block text-[10px] text-content-muted mt-0.5">
          Free tier: {dailyLimit} analysis per 24 hours.{' '}
          <a href="/dashboard/settings/billing" className="text-brand hover:underline">
            Upgrade to Pro
          </a>
        </span>
      </div>
      <span className="text-[10px] text-content-muted">
        {analysesToday}/{dailyLimit}
      </span>
    </div>
  );
}
