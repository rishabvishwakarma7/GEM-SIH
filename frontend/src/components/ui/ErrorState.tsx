import { AlertTriangle, RefreshCw } from 'lucide-react'
import { cn } from '../../lib/cn'
import Button from './Button'

interface ErrorStateProps {
  title?: string
  message?: string
  onRetry?: () => void
  retrying?: boolean
  className?: string
  compact?: boolean
}

/** Standard error panel with an optional retry action. */
export default function ErrorState({
  title = 'Something went wrong',
  message = 'We could not load this content. Please try again.',
  onRetry,
  retrying,
  className,
  compact,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center text-center',
        compact ? 'px-4 py-10' : 'px-6 py-16',
        className,
      )}
    >
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-danger-50 text-danger-500">
        <AlertTriangle className="h-6 w-6" aria-hidden="true" />
      </div>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-slate-500">{message}</p>
      {onRetry ? (
        <Button
          variant="outline"
          size="sm"
          className="mt-5"
          onClick={onRetry}
          loading={retrying}
          leftIcon={<RefreshCw className="h-4 w-4" />}
        >
          Try again
        </Button>
      ) : null}
    </div>
  )
}
