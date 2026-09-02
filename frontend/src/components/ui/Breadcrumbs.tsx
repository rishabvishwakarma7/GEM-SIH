import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { cn } from '../../lib/cn'

export interface BreadcrumbItem {
  label: string
  to?: string
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[]
  className?: string
}

/** Compact breadcrumb trail. The final item renders as the current page. */
export default function Breadcrumbs({ items, className }: BreadcrumbsProps) {
  if (!items.length) return null
  return (
    <nav aria-label="Breadcrumb" className={cn('min-w-0', className)}>
      <ol className="flex items-center gap-1 text-xs text-slate-500">
        {items.map((item, i) => {
          const isLast = i === items.length - 1
          return (
            <li key={`${item.label}-${i}`} className="flex min-w-0 items-center gap-1">
              {item.to && !isLast ? (
                <Link
                  to={item.to}
                  className="truncate rounded px-0.5 font-medium text-slate-500 transition-colors hover:text-primary-700"
                >
                  {item.label}
                </Link>
              ) : (
                <span
                  className={cn(
                    'truncate px-0.5',
                    isLast ? 'font-semibold text-slate-700' : 'text-slate-500',
                  )}
                  aria-current={isLast ? 'page' : undefined}
                >
                  {item.label}
                </span>
              )}
              {!isLast ? (
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-slate-300" aria-hidden="true" />
              ) : null}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
