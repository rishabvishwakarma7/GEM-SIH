import type { ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, Info, XCircle, X } from 'lucide-react'
import { cn } from '../../lib/cn'

export type AlertVariant = 'info' | 'success' | 'warning' | 'danger'

const STYLES: Record<AlertVariant, { wrap: string; icon: ReactNode }> = {
  info: {
    wrap: 'bg-primary-50 border-primary-200 text-primary-800',
    icon: <Info className="h-5 w-5 text-primary-600" />,
  },
  success: {
    wrap: 'bg-success-50 border-success-200 text-success-800',
    icon: <CheckCircle2 className="h-5 w-5 text-success-600" />,
  },
  warning: {
    wrap: 'bg-warning-50 border-warning-200 text-warning-800',
    icon: <AlertTriangle className="h-5 w-5 text-warning-600" />,
  },
  danger: {
    wrap: 'bg-danger-50 border-danger-200 text-danger-800',
    icon: <XCircle className="h-5 w-5 text-danger-600" />,
  },
}

interface AlertProps {
  variant?: AlertVariant
  title?: ReactNode
  children?: ReactNode
  onDismiss?: () => void
  className?: string
}

/** Inline notice for form errors, warnings and confirmations. */
export default function Alert({
  variant = 'info',
  title,
  children,
  onDismiss,
  className,
}: AlertProps) {
  const style = STYLES[variant]
  return (
    <div
      role="alert"
      className={cn(
        'flex items-start gap-3 rounded-lg border px-3.5 py-3 text-sm',
        style.wrap,
        className,
      )}
    >
      <span className="mt-0.5 shrink-0" aria-hidden="true">
        {style.icon}
      </span>
      <div className="min-w-0 flex-1">
        {title ? <p className="font-semibold">{title}</p> : null}
        {children ? (
          <div className={cn('text-[13px] leading-relaxed', title && 'mt-0.5 opacity-90')}>
            {children}
          </div>
        ) : null}
      </div>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded p-0.5 opacity-60 transition-opacity hover:opacity-100"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      ) : null}
    </div>
  )
}
