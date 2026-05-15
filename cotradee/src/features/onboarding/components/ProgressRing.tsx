import { memo } from 'react';

interface Props {
  current: number;
  total: number;
  size?: number;
}

function ProgressRingInner({ current, total, size = 40 }: Props) {
  const strokeWidth = 3;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = total > 0 ? current / total : 0;
  const offset = circumference * (1 - pct);

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0">
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--border)" strokeWidth={strokeWidth} />
      <circle
        cx={size / 2} cy={size / 2} r={radius} fill="none"
        stroke="var(--brand)" strokeWidth={strokeWidth} strokeLinecap="round"
        strokeDasharray={circumference} strokeDashoffset={offset}
        style={{ transition: 'stroke-dashoffset 0.5s cubic-bezier(0.4,0,0.2,1)', transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
      />
      <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" fill="var(--content)" fontSize={size * 0.26} fontWeight={600}>
        {current}/{total}
      </text>
    </svg>
  );
}

export const ProgressRing = memo(ProgressRingInner);
