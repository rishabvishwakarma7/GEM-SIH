import { cn } from '../../lib/cn'

interface SkeletonProps {
  className?: string
}

/** Single shimmer block. Compose these to mirror real content layout. */
export function Skeleton({ className }: SkeletonProps) {
  return <div className={cn('skeleton', className)} />
}

/** A stack of shimmer lines approximating a paragraph. */
export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn('h-3.5', i === lines - 1 ? 'w-2/3' : 'w-full')}
        />
      ))}
    </div>
  )
}

/** Placeholder rows for a loading table body. */
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="divide-y divide-slate-100">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex items-center gap-4 px-4 py-3.5">
          {Array.from({ length: cols }).map((__, c) => (
            <Skeleton
              key={c}
              className={cn('h-4', c === 0 ? 'w-1/4' : 'flex-1')}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

/** Grid of KPI card placeholders. */
export function StatCardSkeleton({ count = 4 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-card border border-slate-200 bg-white p-5 shadow-card">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="mt-3 h-8 w-16" />
        </div>
      ))}
    </>
  )
}

export default Skeleton
