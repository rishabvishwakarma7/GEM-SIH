import { Fragment, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  KeyRound,
  ShieldCheck,
  UserCog,
  Eye,
  CheckCircle2,
  Minus,
  Lock,
} from 'lucide-react'
import Layout from '../../components/Layout'
import { PageHeader, Card, SectionCard, Badge, Alert } from '../../components/ui'
import type { Tone } from '../../components/ui'
import { listUsers } from '../../api/users'
import type { UserRole } from '../../types'
import { ROLE_LABELS, ROLE_DESCRIPTIONS } from '../../lib/roles'

const ROLES: UserRole[] = ['admin', 'evaluator', 'viewer']

const ROLE_META: Record<UserRole, { icon: JSX.Element; tone: Tone }> = {
  admin: { icon: <ShieldCheck className="h-5 w-5" />, tone: 'navy' },
  evaluator: { icon: <UserCog className="h-5 w-5" />, tone: 'primary' },
  viewer: { icon: <Eye className="h-5 w-5" />, tone: 'neutral' },
}

interface Capability {
  label: string
  roles: UserRole[]
}

interface CapGroup {
  category: string
  items: Capability[]
}

/**
 * Static matrix mirroring the backend's real authorization rules
 * (require_roles / isAdmin / canManage / canViewAudit). No fabricated permissions.
 */
const GROUPS: CapGroup[] = [
  {
    category: 'Viewing & reporting',
    items: [
      { label: 'View dashboard & compliance overview', roles: ['admin', 'evaluator', 'viewer'] },
      { label: 'Browse tenders & bidders', roles: ['admin', 'evaluator', 'viewer'] },
      { label: 'View compliance results & evidence', roles: ['admin', 'evaluator', 'viewer'] },
      { label: 'Generate, view & download reports', roles: ['admin', 'evaluator', 'viewer'] },
    ],
  },
  {
    category: 'Evaluation & processing',
    items: [
      { label: 'Create & edit tenders', roles: ['admin', 'evaluator'] },
      { label: 'Create & edit bidders', roles: ['admin', 'evaluator'] },
      { label: 'Upload & process documents', roles: ['admin', 'evaluator'] },
      { label: 'Run AI-assisted verification', roles: ['admin', 'evaluator'] },
      { label: 'Evaluate bidder compliance', roles: ['admin', 'evaluator'] },
      { label: 'View audit trail', roles: ['admin', 'evaluator'] },
    ],
  },
  {
    category: 'Administration',
    items: [
      { label: 'Manage users (create, edit, activate)', roles: ['admin'] },
      { label: 'Assign & change roles', roles: ['admin'] },
      { label: 'Access system settings', roles: ['admin'] },
    ],
  },
]

export default function AdminRoles() {
  const [counts, setCounts] = useState<Record<UserRole, number> | null>(null)

  useEffect(() => {
    // Best-effort user counts per role; the matrix renders regardless.
    listUsers()
      .then((users) => {
        const c: Record<UserRole, number> = { admin: 0, evaluator: 0, viewer: 0 }
        users.forEach((u) => {
          c[u.role] += 1
        })
        setCounts(c)
      })
      .catch(() => setCounts(null))
  }, [])

  const totalCapabilities = useMemo(
    () => GROUPS.reduce((n, g) => n + g.items.length, 0),
    [],
  )

  return (
    <Layout>
      <PageHeader
        icon={<KeyRound className="h-5 w-5" />}
        title="Roles & Permissions"
        description="The three built-in roles and exactly what each one is allowed to do."
        breadcrumbs={[{ label: 'Administration', to: '/admin' }, { label: 'Roles & Permissions' }]}
      />

      {/* Role legend */}
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        {ROLES.map((role) => {
          const meta = ROLE_META[role]
          return (
            <Card key={role} className="flex flex-col gap-3 p-5">
              <div className="flex items-center justify-between">
                <span
                  className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                    meta.tone === 'navy'
                      ? 'bg-navy-50 text-navy-700'
                      : meta.tone === 'primary'
                        ? 'bg-primary-50 text-primary-600'
                        : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  {meta.icon}
                </span>
                {counts ? (
                  <Badge tone="neutral" size="sm">
                    {counts[role]} {counts[role] === 1 ? 'user' : 'users'}
                  </Badge>
                ) : null}
              </div>
              <div>
                <h3 className="font-semibold text-slate-800">{ROLE_LABELS[role]}</h3>
                <p className="mt-1 text-sm text-slate-500">{ROLE_DESCRIPTIONS[role]}</p>
              </div>
            </Card>
          )
        })}
      </div>

      {/* Capability matrix */}
      <SectionCard
        icon={<KeyRound className="h-4 w-4" />}
        title="Permission matrix"
        description={`${totalCapabilities} capabilities across ${ROLES.length} roles.`}
        bodyClassName="p-0"
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-left font-semibold text-slate-600">Capability</th>
                {ROLES.map((role) => (
                  <th
                    key={role}
                    className="px-4 py-3 text-center font-semibold text-slate-600"
                    scope="col"
                  >
                    {ROLE_LABELS[role]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {GROUPS.map((group) => (
                <Fragment key={group.category}>
                  <tr className="bg-slate-50/60">
                    <td
                      colSpan={ROLES.length + 1}
                      className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-400"
                    >
                      {group.category}
                    </td>
                  </tr>
                  {group.items.map((cap) => (
                    <tr key={cap.label} className="border-b border-slate-100 last:border-0">
                      <td className="px-4 py-3 text-slate-700">{cap.label}</td>
                      {ROLES.map((role) => {
                        const granted = cap.roles.includes(role)
                        return (
                          <td key={role} className="px-4 py-3 text-center">
                            {granted ? (
                              <>
                                <CheckCircle2
                                  className="mx-auto h-5 w-5 text-success-600"
                                  aria-hidden="true"
                                />
                                <span className="sr-only">Granted</span>
                              </>
                            ) : (
                              <>
                                <Minus
                                  className="mx-auto h-4 w-4 text-slate-300"
                                  aria-hidden="true"
                                />
                                <span className="sr-only">Not available</span>
                              </>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <Alert variant="info" title="How permissions are enforced" className="mt-6">
        <div className="flex items-start gap-2">
          <Lock className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>
            Roles are fixed and enforced by the backend on every request. Access is determined by a
            user's role regardless of the interface — calling a restricted API without the required
            role returns <span className="font-mono font-semibold">HTTP 403</span>. Assign roles from{' '}
            <Link to="/admin/users" className="font-medium text-primary-600 hover:underline">
              Users
            </Link>
            .
          </p>
        </div>
      </Alert>
    </Layout>
  )
}
