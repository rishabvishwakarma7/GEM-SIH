import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Menu,
  Search,
  Bell,
  ChevronDown,
  User as UserIcon,
  LogOut,
  ShieldCheck,
  AlertTriangle,
  Clock,
  CheckCircle2,
} from 'lucide-react'
import { cn } from '../../lib/cn'
import { useAuth } from '../../context/AuthContext'
import { useClickOutside } from '../../lib/useClickOutside'
import { ROLE_LABELS } from '../../lib/roles'
import { getDashboardStats } from '../../api/dashboard'
import type { DashboardStats } from '../../types'
import Badge from '../ui/Badge'

interface Notice {
  key: string
  label: string
  to: string
  tone: 'warning' | 'danger' | 'neutral'
  icon: typeof AlertTriangle
}

function noticesFromStats(stats: DashboardStats): Notice[] {
  const out: Notice[] = []
  const notEvaluated = Math.max(0, stats.total_bidders - stats.evaluated_bidders)
  if (stats.non_compliant_bidders > 0) {
    out.push({
      key: 'non_compliant',
      label: `${stats.non_compliant_bidders} non-compliant bidder${stats.non_compliant_bidders > 1 ? 's' : ''}`,
      to: '/compliance?status=non_compliant',
      tone: 'danger',
      icon: AlertTriangle,
    })
  }
  if (stats.needs_review_bidders > 0) {
    out.push({
      key: 'needs_review',
      label: `${stats.needs_review_bidders} bidder${stats.needs_review_bidders > 1 ? 's' : ''} need review`,
      to: '/compliance?status=needs_review',
      tone: 'warning',
      icon: Clock,
    })
  }
  if (notEvaluated > 0) {
    out.push({
      key: 'not_evaluated',
      label: `${notEvaluated} bidder${notEvaluated > 1 ? 's' : ''} not yet evaluated`,
      to: '/compliance?status=not_evaluated',
      tone: 'neutral',
      icon: Clock,
    })
  }
  return out
}

interface TopbarProps {
  onOpenMobile: () => void
}

export default function Topbar({ onOpenMobile }: TopbarProps) {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const [term, setTerm] = useState('')

  const [notifOpen, setNotifOpen] = useState(false)
  const [notices, setNotices] = useState<Notice[] | null>(null)
  const notifRef = useRef<HTMLDivElement>(null)
  useClickOutside(notifRef, () => setNotifOpen(false), notifOpen)

  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  useClickOutside(menuRef, () => setMenuOpen(false), menuOpen)

  function submitSearch(e: React.FormEvent) {
    e.preventDefault()
    const q = term.trim()
    navigate(q ? `/compliance?search=${encodeURIComponent(q)}` : '/compliance')
  }

  async function toggleNotifications() {
    const next = !notifOpen
    setNotifOpen(next)
    if (next && notices === null) {
      try {
        const stats = await getDashboardStats()
        setNotices(noticesFromStats(stats))
      } catch {
        setNotices([])
      }
    }
  }

  const alertCount = notices?.length ?? 0

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur supports-[backdrop-filter]:bg-white/75 lg:px-6">
      {/* Mobile menu + brand */}
      <button
        type="button"
        onClick={onOpenMobile}
        className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 lg:hidden"
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>
      <Link to="/dashboard" className="flex items-center gap-2 lg:hidden">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary-600">
          <ShieldCheck className="h-4 w-4 text-white" />
        </span>
        <span className="text-sm font-bold text-slate-900">GeM Compliance</span>
      </Link>

      {/* Global search */}
      <form onSubmit={submitSearch} className="hidden max-w-md flex-1 md:block">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            placeholder="Search bidders by company or GeM seller ID…"
            aria-label="Search bidders"
            className="h-9 w-full rounded-lg border border-slate-300 bg-slate-50 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 transition-colors hover:border-slate-400 focus:border-primary-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500/30"
          />
        </div>
      </form>

      <div className="ml-auto flex items-center gap-1.5">
        {/* Notifications */}
        <div className="relative" ref={notifRef}>
          <button
            type="button"
            onClick={toggleNotifications}
            className="relative rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
            aria-label="Notifications"
            aria-expanded={notifOpen}
          >
            <Bell className="h-5 w-5" />
            {alertCount > 0 && (
              <span className="absolute right-1.5 top-1.5 flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-danger-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-danger-500" />
              </span>
            )}
          </button>
          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 animate-scale-in overflow-hidden rounded-card border border-slate-200 bg-white shadow-elevated">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <p className="text-sm font-semibold text-slate-900">Action items</p>
                {notices ? (
                  <Badge tone={alertCount ? 'warning' : 'success'}>{alertCount}</Badge>
                ) : null}
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notices === null ? (
                  <div className="space-y-2 p-4">
                    <div className="h-4 w-full skeleton" />
                    <div className="h-4 w-2/3 skeleton" />
                  </div>
                ) : notices.length === 0 ? (
                  <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
                    <CheckCircle2 className="h-8 w-8 text-success-500" />
                    <p className="text-sm font-medium text-slate-700">You're all caught up</p>
                    <p className="text-xs text-slate-500">
                      No bidders currently require attention.
                    </p>
                  </div>
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {notices.map((n) => {
                      const Icon = n.icon
                      return (
                        <li key={n.key}>
                          <Link
                            to={n.to}
                            onClick={() => setNotifOpen(false)}
                            className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-slate-50"
                          >
                            <span
                              className={cn(
                                'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
                                n.tone === 'danger' && 'bg-danger-50 text-danger-600',
                                n.tone === 'warning' && 'bg-warning-50 text-warning-600',
                                n.tone === 'neutral' && 'bg-slate-100 text-slate-500',
                              )}
                            >
                              <Icon className="h-4 w-4" />
                            </span>
                            <span className="text-sm text-slate-700">{n.label}</span>
                          </Link>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
              <div className="border-t border-slate-100 bg-slate-50/60 px-4 py-2 text-center">
                <Link
                  to="/compliance"
                  onClick={() => setNotifOpen(false)}
                  className="text-xs font-semibold text-primary-700 hover:text-primary-800"
                >
                  View all compliance results
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* User menu */}
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-2 rounded-lg py-1.5 pl-1.5 pr-2 transition-colors hover:bg-slate-100"
            aria-label="Account menu"
            aria-expanded={menuOpen}
          >
            <span className="grid h-8 w-8 place-items-center rounded-full bg-navy-900 text-xs font-bold text-white">
              {user ? user.full_name.slice(0, 1).toUpperCase() : '?'}
            </span>
            <span className="hidden text-left sm:block">
              <span className="block text-xs font-semibold leading-tight text-slate-800">
                {user?.full_name}
              </span>
              <span className="block text-[11px] leading-tight text-slate-500">
                {user ? ROLE_LABELS[user.role] : ''}
              </span>
            </span>
            <ChevronDown className="hidden h-4 w-4 text-slate-400 sm:block" />
          </button>
          {menuOpen && (
            <div className="absolute right-0 mt-2 w-60 animate-scale-in overflow-hidden rounded-card border border-slate-200 bg-white shadow-elevated">
              <div className="border-b border-slate-100 px-4 py-3">
                <p className="truncate text-sm font-semibold text-slate-900">
                  {user?.full_name}
                </p>
                <p className="truncate text-xs text-slate-500">{user?.email}</p>
                <span className="mt-2 inline-flex">
                  <Badge tone="primary">{user ? ROLE_LABELS[user.role] : ''}</Badge>
                </span>
              </div>
              <div className="p-1.5">
                <Link
                  to="/profile"
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-slate-700 transition-colors hover:bg-slate-100"
                >
                  <UserIcon className="h-4 w-4 text-slate-400" />
                  Profile & security
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false)
                    logout()
                  }}
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-danger-600 transition-colors hover:bg-danger-50"
                >
                  <LogOut className="h-4 w-4" />
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
