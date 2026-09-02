import { cn } from '../../lib/cn'
import type { Tone } from './Badge'

/** Map a 0–100 compliance score to a semantic tone using shared thresholds. */
export function scoreTone(score: number | null | undefined): Tone {
  if (score === null || score === undefined) return 'neutral'
  if (score >= 80) return 'success'
  if (score >= 50) return 'warning'
  return 'danger'
}

const RING_COLOR: Record<Tone, string> = {
  neutral: '#94a3b8',
  primary: '#2563eb',
  navy: '#26395c',
  success: '#059669',
  warning: '#d97706',
  danger: '#dc2626',
  info: '#2563eb',
}

const BAR_COLOR: Record<Tone, string> = {
  neutral: 'bg-slate-400',
  primary: 'bg-primary-500',
  navy: 'bg-navy-600',
  success: 'bg-success-500',
  warning: 'bg-warning-500',
  danger: 'bg-danger-500',
  info: 'bg-primary-500',
}

interface ScoreIndicatorProps {
  score: number | null | undefined
  variant?: 'ring' | 'bar'
  /** Ring diameter in px. */
  size?: number
  className?: string
  /** For the bar variant: show the numeric label beside the track. */
  showValue?: boolean
}

/**
 * Compliance score visualization. `ring` renders an SVG progress ring with the
 * percentage centered; `bar` renders a horizontal track. Both are color-coded
 * by threshold and always show the numeric value (never color alone).
 */
export default function ScoreIndicator({
  score,
  variant = 'ring',
  size = 64,
  className,
  showValue = true,
}: ScoreIndicatorProps) {
  const tone = scoreTone(score)
  const hasScore = score !== null && score !== undefined
  const pct = hasScore ? Math.max(0, Math.min(100, score as number)) : 0

  if (variant === 'bar') {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <div
          className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200"
          role="progressbar"
          aria-valuenow={hasScore ? Math.round(pct) : undefined}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className={cn('h-full rounded-full transition-all', BAR_COLOR[tone])}
            style={{ width: `${pct}%` }}
          />
        </div>
        {showValue ? (
          <span className="w-10 shrink-0 text-right text-xs font-semibold tabular-nums text-slate-700">
            {hasScore ? `${Math.round(pct)}%` : '—'}
          </span>
        ) : null}
      </div>
    )
  }

  const stroke = Math.max(4, Math.round(size * 0.09))
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (pct / 100) * circumference

  return (
    <div
      className={cn('relative inline-flex items-center justify-center', className)}
      style={{ width: size, height: size }}
      role="progressbar"
      aria-valuenow={hasScore ? Math.round(pct) : undefined}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={stroke}
        />
        {hasScore ? (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={RING_COLOR[tone]}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-500"
          />
        ) : null}
      </svg>
      <span
        className="absolute font-bold tabular-nums text-slate-900"
        style={{ fontSize: Math.max(11, size * 0.24) }}
      >
        {hasScore ? Math.round(pct) : '—'}
      </span>
    </div>
  )
}
