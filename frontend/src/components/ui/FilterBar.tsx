import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

interface FilterBarProps {
  /** Primary search control (rendered first, grows to fill space). */
  search?: ReactNode
  /** Filter controls (selects, toggles). */
  children?: ReactNode
  /** Right-aligned actions. */
  actions?: ReactNode
  className?: string
}

/** Responsive toolbar for list pages: search + filters + actions. */
export default function FilterBar({ search, children, actions, className }: FilterBarProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-3 border-b border-slate-200 bg-white p-4 lg:flex-row lg:items-center',
        className,
      )}
    >
      {search ? <div className="w-full lg:max-w-xs">{search}</div> : null}
      {children ? (
        <div className="flex flex-wrap items-center gap-2">{children}</div>
      ) : null}
      {actions ? (
        <div className="flex flex-wrap items-center gap-2 lg:ml-auto">{actions}</div>
      ) : null}
    </div>
  )
}
