import { Loader2 } from 'lucide-react'
import { cn } from '../../lib/cn'

interface SpinnerProps {
  className?: string
  /** Diameter in Tailwind size units via className is preferred; this is a shortcut. */
  size?: number
  label?: string
}

/** Accessible loading spinner built on the lucide Loader2 glyph. */
export default function Spinner({ className, size = 20, label }: SpinnerProps) {
  return (
    <span role="status" aria-live="polite" className="inline-flex items-center gap-2">
      <Loader2
        className={cn('animate-spin text-primary-600', className)}
        style={{ width: size, height: size }}
        aria-hidden="true"
      />
      {label ? <span className="text-sm text-slate-500">{label}</span> : null}
      <span className="sr-only">{label ?? 'Loading'}</span>
    </span>
  )
}
