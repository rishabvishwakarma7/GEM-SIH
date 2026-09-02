import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { cn } from '../../lib/cn'
import type { Tone } from './Badge'

const ICON_TONE: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-600',
  primary: 'bg-primary-50 text-primary-600',
  navy: 'bg-navy-100 text-navy-700',
  success: 'bg-success-50 text-success-600',
  warning: 'bg-warning-50 text-warning-600',
  danger: 'bg-danger-50 text-danger-600',
  info: 'bg-primary-50 text-primary-600',
}

const ACCENT: Record<Tone, string> = {
  neutral: 'before:bg-slate-300',
  primary: 'before:bg-primary-500',
  navy: 'before:bg-navy-500',
  success: 'before:bg-success-500',
  warning: 'before:bg-warning-500',
  danger: 'before:bg-danger-500',
  info: 'before:bg-primary-500',
}

export interface StatCardProps {
  label: string
  value: ReactNode
  icon?: ReactNode
  tone?: Tone
  hint?: ReactNode
  footer?: ReactNode
  to?: string
  loading?: boolean
  className?: string
}

/**
 * KPI / summary card: a large value with a tinted icon, an optional hint line
 * and footer. Renders as a link when `to` is provided. Feeds on real data —
 * pass computed values, never hardcode.
 */
export default function StatCard({
  label,
  value,
  icon,
  tone = 'primary',
  hint,
  footer,
  to,
  loading,
  className,
}: StatCardProps) {
  const inner = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {label}
          </p>
          {loading ? (
            <div className="mt-2 h-8 w-20 skeleton" />
          ) : (
            <p className="mt-1.5 text-2xl font-bold tabular-nums tracking-tight text-slate-900">
              {value}
            </p>
          )}
          {hint && !loading ? (
            <p className="mt-1 text-xs text-slate-500">{hint}</p>
          ) : null}
        </div>
        {icon ? (
          <span
            className={cn(
              'flex h-11 w-11 shrink-0 items-center justify-center rounded-xl',
              ICON_TONE[tone],
            )}
          >
            {icon}
          </span>
        ) : null}
      </div>
      {footer ? <div className="mt-3 border-t border-slate-100 pt-3">{footer}</div> : null}
    </>
  )

  const base = cn(
    'relative overflow-hidden rounded-card border border-slate-200 bg-white p-5 shadow-card',
    "before:absolute before:inset-y-0 before:left-0 before:w-1 before:content-['']",
    ACCENT[tone],
    to && 'transition-shadow hover:shadow-card-hover',
    className,
  )

  if (to) {
    return (
      <Link to={to} className={cn(base, 'block focus-visible:shadow-focus')}>
        {inner}
      </Link>
    )
  }
  return <div className={base}>{inner}</div>
}
