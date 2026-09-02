import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Gauge,
  Users as UsersIcon,
  ShieldCheck,
  UserCog,
  Eye,
  KeyRound,
  Settings,
  ScrollText,
  Activity,
  ArrowRight,
} from 'lucide-react'
import Layout from '../../components/Layout'
import {
  PageHeader,
  StatCard,
  StatCardSkeleton,
  SectionCard,
  Progress,
  EmptyState,
  ErrorState,
  Skeleton,
} from '../../components/ui'
import { listUsers } from '../../api/users'
import { listAuditLogs } from '../../api/audit'
import type { User, UserRole, AuditLogEntry } from '../../types'
import { ROLE_LABELS } from '../../lib/roles'
import { getErrorMessage } from '../../lib/errors'
import { formatRelativeTime } from '../../lib/format'

const ROLE_ORDER: UserRole[] = ['admin', 'evaluator', 'viewer']

const ROLE_BAR: Record<UserRole, 'navy' | 'primary' | 'neutral'> = {
  admin: 'navy',
  evaluator: 'primary',
  viewer: 'neutral',
}

const QUICK_LINKS = [
  {
    to: '/admin/users',
    icon: UsersIcon,
    label: 'Users',
    description: 'Create accounts, assign roles and manage access.',
  },
  {
    to: '/admin/roles',
    icon: KeyRound,
    label: 'Roles & Permissions',
    description: 'Review what each role is allowed to do.',
  },
  {
    to: '/admin/settings',
    icon: Settings,
    label: 'System Settings',
    description: 'Platform status and configuration overview.',
  },
  {
    to: '/audit-logs',
    icon: ScrollText,
    label: 'Audit Logs',
    description: 'Read-only trail of activity across the platform.',
  },
]

function humanizeAction(action: string): string {
  const s = action.replace(/_/g, ' ')
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function actionTone(action: string): { bg: string; fg: string } {
  const a = action.toLowerCase()
  if (a.includes('creat')) return { bg: 'bg-success-50', fg: 'text-success-600' }
  if (a.includes('delet') || a.includes('deactiv') || a.includes('fail'))
    return { bg: 'bg-danger-50', fg: 'text-danger-600' }
  if (a.includes('updat') || a.includes('edit') || a.includes('evaluat'))
    return { bg: 'bg-primary-50', fg: 'text-primary-600' }
  return { bg: 'bg-slate-100', fg: 'text-slate-500' }
}

/** Administrator landing page — real user + audit data, no fabricated metrics. */
export default function AdminOverview() {
  const [users, setUsers] = useState<User[] | null>(null)
  const [usersError, setUsersError] = useState<string | null>(null)

  const [activity, setActivity] = useState<AuditLogEntry[] | null>(null)
  const [activityError, setActivityError] = useState<string | null>(null)

  function loadUsers() {
    setUsersError(null)
    setUsers(null)
    listUsers()
      .then(setUsers)
      .catch((err) => setUsersError(getErrorMessage(err)))
  }

  useEffect(() => {
    loadUsers()
    listAuditLogs({ page: 1, page_size: 6 })
      .then((res) => setActivity(res.items))
      .catch((err) => setActivityError(getErrorMessage(err)))
  }, [])

  const summary = useMemo(() => {
    if (!users) return null
    const byRole: Record<UserRole, number> = { admin: 0, evaluator: 0, viewer: 0 }
    let active = 0
    users.forEach((u) => {
      byRole[u.role] += 1
      if (u.is_active) active += 1
    })
    return { total: users.length, active, inactive: users.length - active, byRole }
  }, [users])

  return (
    <Layout>
      <PageHeader
        icon={<Gauge className="h-5 w-5" />}
        title="Administration"
        description="Manage users, roles and platform configuration."
        breadcrumbs={[{ label: 'Administration' }]}
      />

      {/* User summary */}
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {usersError ? (
          <div className="col-span-2 lg:col-span-4">
            <ErrorState message={usersError} onRetry={loadUsers} compact />
          </div>
        ) : !summary ? (
          <StatCardSkeleton count={4} />
        ) : (
          <>
            <StatCard
              label="Total users"
              value={summary.total}
              icon={<UsersIcon className="h-5 w-5" />}
              tone="primary"
              hint={`${summary.active} active · ${summary.inactive} inactive`}
              to="/admin/users"
            />
            <StatCard
              label="Administrators"
              value={summary.byRole.admin}
              icon={<ShieldCheck className="h-5 w-5" />}
              tone="navy"
              to="/admin/users"
            />
            <StatCard
              label="Evaluators"
              value={summary.byRole.evaluator}
              icon={<UserCog className="h-5 w-5" />}
              tone="primary"
              to="/admin/users"
            />
            <StatCard
              label="Viewers"
              value={summary.byRole.viewer}
              icon={<Eye className="h-5 w-5" />}
              tone="neutral"
              to="/admin/users"
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Recent activity */}
        <div className="lg:col-span-2">
          <SectionCard
            icon={<Activity className="h-4 w-4" />}
            title="Recent activity"
            description="Latest entries from the audit trail."
            actions={
              <Link
                to="/audit-logs"
                className="inline-flex items-center gap-1 text-sm font-medium text-primary-600 hover:text-primary-700"
              >
                View all <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            }
            bodyClassName="p-0"
          >
            {activityError ? (
              <div className="p-4">
                <ErrorState message={activityError} compact />
              </div>
            ) : !activity ? (
              <ul className="divide-y divide-slate-100">
                {Array.from({ length: 5 }).map((_, i) => (
                  <li key={i} className="flex items-center gap-3 px-4 py-3">
                    <Skeleton className="h-8 w-8 rounded-full" />
                    <div className="flex-1 space-y-1.5">
                      <Skeleton className="h-3.5 w-2/5" />
                      <Skeleton className="h-3 w-1/4" />
                    </div>
                  </li>
                ))}
              </ul>
            ) : activity.length === 0 ? (
              <EmptyState
                compact
                icon={<Activity className="h-6 w-6" />}
                title="No activity yet"
                description="Actions taken across the platform will appear here."
              />
            ) : (
              <ul className="divide-y divide-slate-100">
                {activity.map((e) => {
                  const tone = actionTone(e.action)
                  return (
                    <li key={e.id} className="flex items-center gap-3 px-4 py-3">
                      <span
                        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${tone.bg} ${tone.fg}`}
                      >
                        <Activity className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-slate-700">
                          <span className="font-medium">{humanizeAction(e.action)}</span>
                          {e.entity_type ? (
                            <span className="text-slate-400"> · {e.entity_type}</span>
                          ) : null}
                        </p>
                        <p className="truncate text-xs text-slate-400">{e.user_name ?? 'System'}</p>
                      </div>
                      <time className="shrink-0 text-xs text-slate-400">
                        {formatRelativeTime(e.created_at)}
                      </time>
                    </li>
                  )
                })}
              </ul>
            )}
          </SectionCard>
        </div>

        {/* Side column */}
        <div className="space-y-6">
          <SectionCard icon={<UsersIcon className="h-4 w-4" />} title="Role distribution">
            {!summary ? (
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {ROLE_ORDER.map((role) => {
                  const count = summary.byRole[role]
                  const pct = summary.total ? Math.round((count / summary.total) * 100) : 0
                  return (
                    <div key={role}>
                      <div className="mb-1 flex items-center justify-between text-sm">
                        <span className="font-medium text-slate-700">{ROLE_LABELS[role]}</span>
                        <span className="tabular-nums text-slate-500">
                          {count} · {pct}%
                        </span>
                      </div>
                      <Progress value={pct} tone={ROLE_BAR[role]} />
                    </div>
                  )
                })}
              </div>
            )}
          </SectionCard>

          <SectionCard icon={<Settings className="h-4 w-4" />} title="Manage" bodyClassName="p-0">
            <ul className="divide-y divide-slate-100">
              {QUICK_LINKS.map((link) => {
                const Icon = link.icon
                return (
                  <li key={link.to}>
                    <Link
                      to={link.to}
                      className="group flex items-center gap-3 px-4 py-3 transition-colors hover:bg-slate-50"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500 group-hover:bg-primary-50 group-hover:text-primary-600">
                        <Icon className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-slate-800">{link.label}</p>
                        <p className="truncate text-xs text-slate-400">{link.description}</p>
                      </div>
                      <ArrowRight className="h-4 w-4 shrink-0 text-slate-300 group-hover:text-primary-500" />
                    </Link>
                  </li>
                )
              })}
            </ul>
          </SectionCard>
        </div>
      </div>
    </Layout>
  )
}
