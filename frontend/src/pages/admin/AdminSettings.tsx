import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Settings,
  Server,
  ShieldCheck,
  KeyRound,
  Sparkles,
  Database,
  ScrollText,
  UserCircle,
  CheckCircle2,
  XCircle,
} from 'lucide-react'
import Layout from '../../components/Layout'
import { PageHeader, SectionCard, Alert, Badge, StatusBadge, Spinner } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { ROLE_LABELS } from '../../lib/roles'
import apiClient from '../../api/client'

type Health = 'checking' | 'ok' | 'down'

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="text-sm font-medium text-slate-800">{children}</dd>
    </div>
  )
}

/**
 * Read-only overview of how the platform is configured. Intentionally shows only
 * real, verifiable information (live backend health, build mode, the signed-in
 * session, fixed roles) — there are no fabricated, mutable settings toggles.
 */
export default function AdminSettings() {
  const { user } = useAuth()
  const [health, setHealth] = useState<Health>('checking')

  const env = import.meta.env.MODE
  const isDev = import.meta.env.DEV

  function checkHealth() {
    setHealth('checking')
    apiClient
      .get('/health')
      .then(() => setHealth('ok'))
      .catch(() => setHealth('down'))
  }

  useEffect(() => {
    checkHealth()
  }, [])

  return (
    <Layout>
      <PageHeader
        icon={<Settings className="h-5 w-5" />}
        title="System Settings"
        description="Platform status and configuration overview."
        breadcrumbs={[{ label: 'Administration', to: '/admin' }, { label: 'System Settings' }]}
      />

      <Alert variant="info" title="Read-only overview" className="mb-6">
        This page summarizes how the platform is configured. These values are managed by system
        administrators outside the application and cannot be edited here.
      </Alert>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Platform status */}
        <SectionCard icon={<Server className="h-4 w-4" />} title="Platform status">
          <dl className="divide-y divide-slate-100">
            <Row label="Backend API">
              {health === 'checking' ? (
                <span className="inline-flex items-center gap-1.5 text-slate-500">
                  <Spinner size={16} /> Checking…
                </span>
              ) : health === 'ok' ? (
                <StatusBadge tone="success" icon={<CheckCircle2 className="h-3.5 w-3.5" />}>
                  Operational
                </StatusBadge>
              ) : (
                <button
                  onClick={checkHealth}
                  className="inline-flex items-center gap-1.5"
                  title="Retry"
                >
                  <StatusBadge tone="danger" icon={<XCircle className="h-3.5 w-3.5" />}>
                    Unavailable
                  </StatusBadge>
                </button>
              )}
            </Row>
            <Row label="Environment">
              <Badge tone={isDev ? 'warning' : 'success'}>{env}</Badge>
            </Row>
            <Row label="API endpoint">
              <span className="font-mono text-xs">{apiClient.defaults.baseURL}</span>
            </Row>
            <Row label="Interface">Single-page web application (React)</Row>
          </dl>
        </SectionCard>

        {/* Your session */}
        <SectionCard icon={<UserCircle className="h-4 w-4" />} title="Your session">
          <dl className="divide-y divide-slate-100">
            <Row label="Signed in as">{user?.full_name ?? '—'}</Row>
            <Row label="Email">
              <span className="font-normal text-slate-600">{user?.email ?? '—'}</span>
            </Row>
            <Row label="Role">
              {user ? <Badge tone="navy">{ROLE_LABELS[user.role]}</Badge> : '—'}
            </Row>
            <Row label="Authentication">JWT bearer token (expires on sign-out)</Row>
          </dl>
          <div className="mt-4 border-t border-slate-100 pt-4">
            <Link
              to="/profile"
              className="text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              Manage your profile & password →
            </Link>
          </div>
        </SectionCard>

        {/* Access control */}
        <SectionCard icon={<ShieldCheck className="h-4 w-4" />} title="Access control">
          <p className="text-sm text-slate-600">
            Three fixed roles govern access. Authorization is enforced by the backend on every
            request — a user cannot exceed their role by calling APIs directly.
          </p>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            <li className="flex items-center gap-2">
              <Badge tone="navy" size="sm">
                {ROLE_LABELS.admin}
              </Badge>
              Full access incl. user & role management
            </li>
            <li className="flex items-center gap-2">
              <Badge tone="primary" size="sm">
                {ROLE_LABELS.evaluator}
              </Badge>
              Manage tenders/bidders, run verification & evaluate
            </li>
            <li className="flex items-center gap-2">
              <Badge tone="neutral" size="sm">
                {ROLE_LABELS.viewer}
              </Badge>
              Read-only access
            </li>
          </ul>
          <div className="mt-4 flex flex-wrap gap-4 border-t border-slate-100 pt-4 text-sm font-medium">
            <Link
              to="/admin/roles"
              className="inline-flex items-center gap-1.5 text-primary-600 hover:text-primary-700"
            >
              <KeyRound className="h-4 w-4" /> Roles & Permissions
            </Link>
            <Link
              to="/admin/users"
              className="inline-flex items-center gap-1.5 text-primary-600 hover:text-primary-700"
            >
              <ShieldCheck className="h-4 w-4" /> Manage users
            </Link>
          </div>
        </SectionCard>

        {/* AI-assisted verification */}
        <SectionCard icon={<Sparkles className="h-4 w-4" />} title="AI-assisted verification">
          <p className="text-sm text-slate-600">
            Document extraction and requirement matching are performed with AI assistance (Google
            Gemini). AI output is a decision aid, not a final ruling.
          </p>
          <ul className="mt-3 list-inside list-disc space-y-1 text-sm text-slate-600">
            <li>Confidence scores accompany extracted data; low-confidence items are flagged.</li>
            <li>Some registry / authenticity checks are simulated for demonstration.</li>
            <li>Flagged items should be verified by an evaluator against the source document.</li>
          </ul>
        </SectionCard>

        {/* Data & audit */}
        <SectionCard
          icon={<Database className="h-4 w-4" />}
          title="Data & audit"
          className="lg:col-span-2"
        >
          <dl className="divide-y divide-slate-100">
            <Row label="Document processing">Server-side text extraction &amp; OCR</Row>
            <Row label="Audit trail">
              <span className="inline-flex items-center gap-1.5">
                <ScrollText className="h-3.5 w-3.5 text-slate-400" />
                Append-only, read-only
              </span>
            </Row>
            <Row label="Data retention">Records are preserved; the database is never reset by the app</Row>
          </dl>
          <div className="mt-4 border-t border-slate-100 pt-4">
            <Link
              to="/audit-logs"
              className="text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              View audit logs →
            </Link>
          </div>
        </SectionCard>
      </div>
    </Layout>
  )
}
