import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Removes inner padding when you need full-bleed content (e.g. a table). */
  flush?: boolean
  hover?: boolean
}

/** Base white surface with border + subtle shadow. */
export function Card({ flush, hover, className, children, ...rest }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-card border border-slate-200 bg-white shadow-card',
        hover && 'transition-shadow hover:shadow-card-hover',
        !flush && 'p-5',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}

export interface SectionCardProps {
  title?: ReactNode
  description?: ReactNode
  icon?: ReactNode
  actions?: ReactNode
  /** Remove body padding (for tables that manage their own spacing). */
  flush?: boolean
  className?: string
  bodyClassName?: string
  children: ReactNode
}

/**
 * A titled content section: header row (icon + title + description + actions)
 * above a bordered body. The workhorse container for detail pages.
 */
export function SectionCard({
  title,
  description,
  icon,
  actions,
  flush,
  className,
  bodyClassName,
  children,
}: SectionCardProps) {
  const hasHeader = title || description || actions || icon
  return (
    <section
      className={cn(
        'overflow-hidden rounded-card border border-slate-200 bg-white shadow-card',
        className,
      )}
    >
      {hasHeader ? (
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 bg-slate-50/60 px-5 py-3.5">
          <div className="flex min-w-0 items-start gap-3">
            {icon ? (
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-50 text-primary-600">
                {icon}
              </span>
            ) : null}
            <div className="min-w-0">
              {title ? (
                <h3 className="truncate text-sm font-semibold text-slate-900">
                  {title}
                </h3>
              ) : null}
              {description ? (
                <p className="mt-0.5 text-xs text-slate-500">{description}</p>
              ) : null}
            </div>
          </div>
          {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
        </header>
      ) : null}
      <div className={cn(!flush && 'p-5', bodyClassName)}>{children}</div>
    </section>
  )
}

export default Card
