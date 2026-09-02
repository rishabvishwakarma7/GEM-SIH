import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'
import Breadcrumbs from './Breadcrumbs'
import type { BreadcrumbItem } from './Breadcrumbs'

interface PageHeaderProps {
  title: ReactNode
  description?: ReactNode
  icon?: ReactNode
  breadcrumbs?: BreadcrumbItem[]
  actions?: ReactNode
  className?: string
}

/**
 * Standard page title block: breadcrumbs, an optional brand icon, the page
 * title + description, and a right-aligned actions slot. Used at the top of
 * every content page for a consistent rhythm.
 */
export default function PageHeader({
  title,
  description,
  icon,
  breadcrumbs,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn('mb-6', className)}>
      {breadcrumbs && breadcrumbs.length ? (
        <Breadcrumbs items={breadcrumbs} className="mb-2.5" />
      ) : null}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          {icon ? (
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-gradient text-white shadow-sm">
              {icon}
            </span>
          ) : null}
          <div className="min-w-0">
            <h1 className="truncate text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
              {title}
            </h1>
            {description ? (
              <p className="mt-1 max-w-2xl text-sm text-slate-500">{description}</p>
            ) : null}
          </div>
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
    </div>
  )
}
