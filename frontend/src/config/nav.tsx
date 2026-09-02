import {
  LayoutDashboard,
  FileText,
  Building2,
  ShieldCheck,
  FileBarChart2,
  ScrollText,
  Users,
  KeyRound,
  Settings,
  Gauge,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { UserRole } from '../types'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  /** When set, item is only shown to these roles. Undefined = all authenticated. */
  roles?: UserRole[]
  /** Match the route exactly (for index-like routes). */
  end?: boolean
  /** Extra path prefixes that should also mark this item active. */
  activePaths?: string[]
}

export interface NavSection {
  label?: string
  items: NavItem[]
}

export const NAV_SECTIONS: NavSection[] = [
  {
    items: [
      { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
      {
        label: 'Tenders',
        to: '/tenders',
        icon: FileText,
        activePaths: ['/tenders'],
      },
      {
        label: 'Bidders',
        to: '/bidders',
        icon: Building2,
        activePaths: ['/bidders'],
      },
      { label: 'Compliance', to: '/compliance', icon: ShieldCheck },
      { label: 'Reports', to: '/reports', icon: FileBarChart2 },
    ],
  },
  {
    label: 'Administration',
    items: [
      { label: 'Admin Overview', to: '/admin', icon: Gauge, roles: ['admin'], end: true },
      { label: 'Users', to: '/admin/users', icon: Users, roles: ['admin'] },
      {
        label: 'Roles & Permissions',
        to: '/admin/roles',
        icon: KeyRound,
        roles: ['admin'],
      },
      { label: 'System Settings', to: '/admin/settings', icon: Settings, roles: ['admin'] },
      {
        label: 'Audit Logs',
        to: '/audit-logs',
        icon: ScrollText,
        roles: ['admin', 'evaluator'],
      },
    ],
  },
]

/** Filter nav sections/items by the current user's role. */
export function visibleSections(role: UserRole | undefined): NavSection[] {
  if (!role) return []
  return NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => !item.roles || item.roles.includes(role)),
  })).filter((section) => section.items.length > 0)
}
