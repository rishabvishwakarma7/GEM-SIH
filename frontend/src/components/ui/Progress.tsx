import { cn } from '../../lib/cn'
import type { Tone } from './Badge'

const BAR: Record<Tone, string> = {
  neutral: 'bg-slate-400',
  primary: 'bg-primary-500',
  navy: 'bg-navy-600',
  success: 'bg-success-500',
  warning: 'bg-warning-500',
  danger: 'bg-danger-500',
  info: 'bg-primary-500',
}

interface ProgressProps {
  /** 0–100. */
  value: number
  tone?: Tone
  className?: string
  /** Animated candy-stripe for indeterminate-feel processing. */
  striped?: boolean
}

/** Horizontal progress track for uploads and processing stages. */
export default function Progress({ value, tone = 'primary', className, striped }: ProgressProps) {
  const pct = Math.max(0, Math.min(100, value))
  return (
    <div
      className={cn('h-2 w-full overflow-hidden rounded-full bg-slate-200', className)}
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={cn(
          'h-full rounded-full transition-all duration-500 ease-out',
          BAR[tone],
          striped &&
            'bg-[length:1rem_1rem] bg-gradient-to-r from-white/0 via-white/25 to-white/0',
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
