import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'
import { TONE_STYLES } from './Badge'
import type { Tone } from './Badge'

const DOT_STYLES: Record<Tone, string> = {
  neutral: 'bg-slate-400',
  primary: 'bg-primary-500',
  navy: 'bg-navy-500',
  success: 'bg-success-500',
  warning: 'bg-warning-500',
  danger: 'bg-danger-500',
  info: 'bg-primary-500',
}

export interface StatusBadgeProps {
  tone?: Tone
  /** Optional leading icon (e.g. a lucide glyph). Overrides the colored dot. */
  icon?: ReactNode
  /** Show a colored status dot when no icon is provided. */
  dot?: boolean
  size?: 'sm' | 'md'
  className?: string
  children: ReactNode
}

/**
 * Semantic status pill: color + icon/dot + text label together, so status is
 * never conveyed by color alone (accessibility requirement).
 */
export default function StatusBadge({
  tone = 'neutral',
  icon,
  dot = true,
  size = 'md',
  className,
  children,
}: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-semibold leading-none',
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs',
        TONE_STYLES[tone],
        className,
      )}
    >
      {icon ? (
        <span className="inline-flex shrink-0 items-center" aria-hidden="true">
          {icon}
        </span>
      ) : dot ? (
        <span
          className={cn('h-1.5 w-1.5 shrink-0 rounded-full', DOT_STYLES[tone])}
          aria-hidden="true"
        />
      ) : null}
      <span>{children}</span>
    </span>
  )
}
