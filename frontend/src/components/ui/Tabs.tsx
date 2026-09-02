import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

export interface TabItem {
  key: string
  label: string
  icon?: ReactNode
  count?: number
  disabled?: boolean
}

interface TabsProps {
  tabs: TabItem[]
  active: string
  onChange: (key: string) => void
  className?: string
}

/** Horizontal, scrollable tab bar with an underline active indicator. */
export default function Tabs({ tabs, active, onChange, className }: TabsProps) {
  return (
    <div className={cn('border-b border-slate-200', className)}>
      <div
        role="tablist"
        aria-label="Sections"
        className="-mb-px flex gap-1 overflow-x-auto"
      >
        {tabs.map((tab) => {
          const selected = tab.key === active
          return (
            <button
              key={tab.key}
              role="tab"
              type="button"
              aria-selected={selected}
              disabled={tab.disabled}
              onClick={() => onChange(tab.key)}
              className={cn(
                'inline-flex shrink-0 items-center gap-2 whitespace-nowrap border-b-2 px-3.5 py-2.5 text-sm font-semibold transition-colors',
                'disabled:cursor-not-allowed disabled:opacity-40',
                selected
                  ? 'border-primary-600 text-primary-700'
                  : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800',
              )}
            >
              {tab.icon ? (
                <span className="shrink-0" aria-hidden="true">
                  {tab.icon}
                </span>
              ) : null}
              {tab.label}
              {typeof tab.count === 'number' ? (
                <span
                  className={cn(
                    'rounded-full px-1.5 py-0.5 text-[11px] font-semibold tabular-nums',
                    selected
                      ? 'bg-primary-100 text-primary-700'
                      : 'bg-slate-100 text-slate-500',
                  )}
                >
                  {tab.count}
                </span>
              ) : null}
            </button>
          )
        })}
      </div>
    </div>
  )
}
