// Barrel export for the shared UI primitive library.
export { default as Button } from './Button'
export type { ButtonProps, ButtonVariant, ButtonSize } from './Button'

export { default as Badge, TONE_STYLES } from './Badge'
export type { Tone, BadgeProps } from './Badge'

export { default as StatusBadge } from './StatusBadge'
export type { StatusBadgeProps } from './StatusBadge'

export { Card, SectionCard } from './Card'
export type { CardProps, SectionCardProps } from './Card'

export { default as PageHeader } from './PageHeader'
export { default as Breadcrumbs } from './Breadcrumbs'
export type { BreadcrumbItem } from './Breadcrumbs'

export { default as StatCard } from './StatCard'
export type { StatCardProps } from './StatCard'

export { default as ScoreIndicator, scoreTone } from './ScoreIndicator'

export { default as Tabs } from './Tabs'
export type { TabItem } from './Tabs'

export { default as EmptyState } from './EmptyState'
export { default as ErrorState } from './ErrorState'

export {
  Skeleton,
  SkeletonText,
  TableSkeleton,
  StatCardSkeleton,
} from './Skeleton'

export { default as Alert } from './Alert'
export type { AlertVariant } from './Alert'

export { default as Modal } from './Modal'
export type { ModalSize } from './Modal'

export { default as ConfirmDialog } from './ConfirmDialog'
export { default as Spinner } from './Spinner'

export { default as DataTable } from './DataTable'
export type { Column } from './DataTable'

export { default as Pagination } from './Pagination'
export { default as FilterBar } from './FilterBar'
export { default as Progress } from './Progress'

export { Input, Textarea, Select, Label, FormField } from './Field'
export type { InputProps, TextareaProps, SelectProps, LabelProps } from './Field'
