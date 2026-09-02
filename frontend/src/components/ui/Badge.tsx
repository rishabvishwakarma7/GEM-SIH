import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

export type Tone =
  | 'neutral'
  | 'primary'
  | 'navy'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'

export const TONE_STYLES: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-700 border-slate-200',
  primary: 'bg-primary-50 text-primary-700 border-primary-200',
  navy: 'bg-navy-100 text-navy-800 border-navy-200',
  success: 'bg-success-50 text-success-700 border-success-200',
  warning: 'bg-warning-50 text-warning-800 border-warning-200',
  danger: 'bg-danger-50 text-danger-700 border-danger-200',
  info: 'bg-primary-50 text-primary-700 border-primary-200',
}

const SIZE_STYLES = {
  sm: 'px-1.5 py-0.5 text-[11px]',
  md: 'px-2 py-0.5 text-xs',
} as const

export interface BadgeProps {
  tone?: Tone
  size?: keyof typeof SIZE_STYLES
  className?: string
  /** Native tooltip text. */
  title?: string
  children: ReactNode
}

/** Generic, tone-based pill. Building block for semantic status chips. */
export default function Badge({
  tone = 'neutral',
  size = 'md',
  className,
  title,
  children,
}: BadgeProps) {
  return (
    <span
      title={title}
      className={cn(
        'inline-flex items-center gap-1 rounded-full border font-semibold leading-none',
        TONE_STYLES[tone],
        SIZE_STYLES[size],
        className,
      )}
    >
      {children}
    </span>
  )
}
