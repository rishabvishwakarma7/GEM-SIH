import { NavLink } from 'react-router-dom'
import {
  ShieldCheck,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from 'lucide-react'
import { cn } from '../../lib/cn'
import { useAuth } from '../../context/AuthContext'
import { visibleSections } from '../../config/nav'
import { ROLE_LABELS } from '../../lib/roles'

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

const ROW =
  'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-primary-400/70'
const ROW_ACTIVE =
  'bg-white/10 text-white before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-1 before:rounded-r before:bg-primary-400'
const ROW_INACTIVE = 'text-navy-200 hover:bg-white/5 hover:text-white'

interface InnerProps {
  collapsed: boolean
  onNavigate?: () => void
}

function SidebarInner({ collapsed, onNavigate }: InnerProps) {
  const { user, logout } = useAuth()
  const sections = visibleSections(user?.role)

  return (
    <div className="flex h-full flex-col bg-sidebar-gradient">
      {/* Brand */}
      <div
        className={cn(
          'flex h-16 shrink-0 items-center border-b border-white/10 px-4',
          collapsed && 'justify-center px-0',
        )}
      >
        <div className="flex items-center gap-2.5">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary-600 shadow-sm">
            <ShieldCheck className="h-5 w-5 text-white" aria-hidden="true" />
          </div>
          {!collapsed && (
            <div className="leading-tight">
              <p className="text-sm font-bold text-white">GeM Compliance</p>
              <p className="text-[11px] font-medium text-navy-300">CPCL · SIH 2026</p>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="scrollbar-dark flex-1 space-y-6 overflow-y-auto px-3 py-4">
        {sections.map((section, si) => (
          <div key={section.label ?? si}>
            {section.label && !collapsed ? (
              <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-navy-400">
                {section.label}
              </p>
            ) : section.label && collapsed ? (
              <div className="mx-3 mb-2 border-t border-white/10" />
            ) : null}
            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    onClick={onNavigate}
                    title={collapsed ? item.label : undefined}
                    className={({ isActive }) =>
                      cn(ROW, collapsed && 'justify-center px-0', isActive ? ROW_ACTIVE : ROW_INACTIVE)
                    }
                  >
                    <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                    {collapsed && (
                      <span className="pointer-events-none absolute left-full z-50 ml-2 hidden whitespace-nowrap rounded-md bg-navy-950 px-2 py-1 text-xs font-medium text-white shadow-lg group-hover:block">
                        {item.label}
                      </span>
                    )}
                  </NavLink>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="shrink-0 border-t border-white/10 p-3">
        <div className={cn('flex items-center gap-2.5', collapsed && 'flex-col gap-2')}>
          <NavLink
            to="/profile"
            onClick={onNavigate}
            title={collapsed ? user?.full_name : undefined}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-primary-500/20 text-xs font-bold text-white ring-1 ring-white/20 transition-colors hover:bg-primary-500/30"
          >
            {user ? initialsOf(user.full_name) : '?'}
          </NavLink>
          {!collapsed && (
            <>
              <NavLink to="/profile" onClick={onNavigate} className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-white">
                  {user?.full_name ?? 'Account'}
                </p>
                <p className="truncate text-[11px] text-navy-300">
                  {user ? ROLE_LABELS[user.role] : ''}
                </p>
              </NavLink>
              <button
                type="button"
                onClick={logout}
                title="Sign out"
                aria-label="Sign out"
                className="shrink-0 rounded-lg p-2 text-navy-300 transition-colors hover:bg-white/10 hover:text-white"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </>
          )}
          {collapsed && (
            <button
              type="button"
              onClick={logout}
              title="Sign out"
              aria-label="Sign out"
              className="rounded-lg p-2 text-navy-300 transition-colors hover:bg-white/10 hover:text-white"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

interface SidebarProps {
  collapsed: boolean
  mobileOpen: boolean
  onCloseMobile: () => void
  onToggleCollapse: () => void
}

export default function Sidebar({
  collapsed,
  mobileOpen,
  onCloseMobile,
  onToggleCollapse,
}: SidebarProps) {
  return (
    <>
      {/* Desktop rail */}
      <aside
        className={cn(
          'sticky top-0 hidden h-screen shrink-0 flex-col lg:flex',
          collapsed ? 'w-[76px]' : 'w-64',
        )}
      >
        <div className="relative flex-1 overflow-hidden">
          <SidebarInner collapsed={collapsed} />
        </div>
        <button
          type="button"
          onClick={onToggleCollapse}
          className="flex h-10 shrink-0 items-center justify-center gap-2 border-t border-white/10 bg-navy-950 text-xs font-medium text-navy-300 transition-colors hover:bg-navy-900 hover:text-white"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <PanelLeftOpen className="h-4 w-4" />
          ) : (
            <>
              <PanelLeftClose className="h-4 w-4" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-navy-950/60 backdrop-blur-[2px] animate-fade-in"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <div className="absolute inset-y-0 left-0 w-64 animate-slide-up shadow-elevated">
            <button
              type="button"
              onClick={onCloseMobile}
              className="absolute right-3 top-4 z-10 rounded-lg p-1.5 text-navy-300 transition-colors hover:bg-white/10 hover:text-white"
              aria-label="Close menu"
            >
              <X className="h-5 w-5" />
            </button>
            <SidebarInner collapsed={false} onNavigate={onCloseMobile} />
          </div>
        </div>
      )}
    </>
  )
}
