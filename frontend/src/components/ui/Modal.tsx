import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { X } from 'lucide-react'
import { cn } from '../../lib/cn'

export type ModalSize = 'sm' | 'md' | 'lg' | 'xl'

const SIZES: Record<ModalSize, string> = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
}

interface ModalProps {
  open: boolean
  onClose: () => void
  title?: ReactNode
  description?: ReactNode
  icon?: ReactNode
  footer?: ReactNode
  size?: ModalSize
  children: ReactNode
  /** Prevent closing on backdrop click (e.g. while an action is in flight). */
  disableBackdropClose?: boolean
}

/** Accessible centered dialog with backdrop, Escape-to-close and scroll lock. */
export default function Modal({
  open,
  onClose,
  title,
  description,
  icon,
  footer,
  size = 'md',
  children,
  disableBackdropClose,
}: ModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:items-center sm:p-6"
      aria-hidden={false}
    >
      <div
        className="fixed inset-0 bg-navy-950/50 backdrop-blur-[2px] animate-fade-in"
        onClick={disableBackdropClose ? undefined : onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          'relative z-10 my-auto w-full animate-scale-in rounded-card border border-slate-200 bg-white shadow-elevated',
          SIZES[size],
        )}
      >
        {(title || icon) && (
          <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
            <div className="flex min-w-0 items-start gap-3">
              {icon ? (
                <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-50 text-primary-600">
                  {icon}
                </span>
              ) : null}
              <div className="min-w-0">
                {title ? (
                  <h2 className="text-base font-semibold text-slate-900">{title}</h2>
                ) : null}
                {description ? (
                  <p className="mt-0.5 text-sm text-slate-500">{description}</p>
                ) : null}
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="shrink-0 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
              aria-label="Close dialog"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        )}
        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer ? (
          <div className="flex items-center justify-end gap-2 border-t border-slate-200 bg-slate-50/60 px-5 py-3.5">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  )
}
