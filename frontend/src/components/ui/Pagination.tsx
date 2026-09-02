import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '../../lib/cn'
import Button from './Button'

interface PaginationProps {
  page: number
  totalPages: number
  total?: number
  pageSize?: number
  onPageChange: (page: number) => void
  className?: string
}

/** Range summary + prev/next controls. Hidden entirely when there's one page. */
export default function Pagination({
  page,
  totalPages,
  total,
  pageSize,
  onPageChange,
  className,
}: PaginationProps) {
  const showRange = typeof total === 'number' && typeof pageSize === 'number' && total > 0
  const from = showRange ? (page - 1) * (pageSize as number) + 1 : 0
  const to = showRange ? Math.min(page * (pageSize as number), total as number) : 0

  if (totalPages <= 1 && !showRange) return null

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 sm:flex-row',
        className,
      )}
    >
      <p className="text-xs text-slate-500">
        {showRange ? (
          <>
            Showing <span className="font-semibold text-slate-700">{from}</span>–
            <span className="font-semibold text-slate-700">{to}</span> of{' '}
            <span className="font-semibold text-slate-700">{total}</span>
          </>
        ) : (
          <>
            Page <span className="font-semibold text-slate-700">{page}</span> of{' '}
            <span className="font-semibold text-slate-700">{totalPages}</span>
          </>
        )}
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          leftIcon={<ChevronLeft className="h-4 w-4" />}
        >
          Previous
        </Button>
        <span className="px-1 text-xs font-medium text-slate-500 tabular-nums">
          {page} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          rightIcon={<ChevronRight className="h-4 w-4" />}
        >
          Next
        </Button>
      </div>
    </div>
  )
}
