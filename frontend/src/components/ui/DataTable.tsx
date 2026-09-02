import type { ReactNode } from 'react'
import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react'
import { cn } from '../../lib/cn'
import { TableSkeleton } from './Skeleton'

export interface Column<T> {
  key: string
  header: ReactNode
  /** Cell renderer. Falls back to nothing if omitted. */
  render?: (row: T, index: number) => ReactNode
  align?: 'left' | 'center' | 'right'
  className?: string
  headerClassName?: string
  /** Enables the clickable sort header; uses `sortKey` (or `key`) as the id. */
  sortable?: boolean
  sortKey?: string
  /** Hide below the `sm` breakpoint to keep mobile tables readable. */
  hideOnMobile?: boolean
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  rowKey: (row: T, index: number) => string
  onRowClick?: (row: T) => void
  sortBy?: string
  sortDir?: 'asc' | 'desc'
  onSort?: (key: string) => void
  loading?: boolean
  skeletonRows?: number
  empty?: ReactNode
  className?: string
}

const ALIGN: Record<'left' | 'center' | 'right', string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
}

/** Generic, typed, responsive (horizontally scrollable) table. */
export default function DataTable<T>({
  columns,
  data,
  rowKey,
  onRowClick,
  sortBy,
  sortDir,
  onSort,
  loading,
  skeletonRows = 6,
  empty,
  className,
}: DataTableProps<T>) {
  if (loading) {
    return <TableSkeleton rows={skeletonRows} cols={columns.length} />
  }

  if (!data.length && empty) {
    return <>{empty}</>
  }

  return (
    <div className={cn('w-full overflow-x-auto', className)}>
      <table className="min-w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50/80">
            {columns.map((col) => {
              const align = col.align ?? 'left'
              const id = col.sortKey ?? col.key
              const isSorted = sortBy === id
              return (
                <th
                  key={col.key}
                  scope="col"
                  className={cn(
                    'px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500',
                    ALIGN[align],
                    col.hideOnMobile && 'hidden sm:table-cell',
                    col.headerClassName,
                  )}
                >
                  {col.sortable && onSort ? (
                    <button
                      type="button"
                      onClick={() => onSort(id)}
                      className={cn(
                        'inline-flex items-center gap-1 rounded transition-colors hover:text-slate-800',
                        align === 'right' && 'flex-row-reverse',
                        isSorted && 'text-slate-800',
                      )}
                    >
                      {col.header}
                      {isSorted ? (
                        sortDir === 'desc' ? (
                          <ArrowDown className="h-3.5 w-3.5" />
                        ) : (
                          <ArrowUp className="h-3.5 w-3.5" />
                        )
                      ) : (
                        <ChevronsUpDown className="h-3.5 w-3.5 text-slate-300" />
                      )}
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {data.map((row, index) => (
            <tr
              key={rowKey(row, index)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn(
                'bg-white transition-colors',
                onRowClick && 'cursor-pointer hover:bg-slate-50',
              )}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn(
                    'px-4 py-3 align-middle text-slate-700',
                    ALIGN[col.align ?? 'left'],
                    col.hideOnMobile && 'hidden sm:table-cell',
                    col.className,
                  )}
                >
                  {col.render ? col.render(row, index) : null}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
