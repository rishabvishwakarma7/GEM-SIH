import { Link } from 'react-router-dom'
import { ShieldAlert, ArrowLeft, LayoutDashboard } from 'lucide-react'
import Layout from '../components/Layout'
import { useAuth } from '../context/AuthContext'
import { ROLE_LABELS } from '../lib/roles'
import Button from '../components/ui/Button'

/**
 * 403 page shown when an authenticated user reaches a route their role is not
 * permitted to access. Rendered in-shell so they can navigate elsewhere.
 * (Backend authorization is enforced independently and returns real 403s.)
 */
export default function Unauthorized() {
  const { user } = useAuth()
  return (
    <Layout>
      <div className="mx-auto flex max-w-lg flex-col items-center justify-center py-16 text-center">
        <div className="mb-5 grid h-16 w-16 place-items-center rounded-2xl bg-danger-50 text-danger-500">
          <ShieldAlert className="h-8 w-8" />
        </div>
        <p className="text-xs font-bold uppercase tracking-wider text-danger-600">
          403 · Access restricted
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
          You don't have permission to view this page
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          This area is limited to administrators. Your account is currently signed in as{' '}
          <span className="font-semibold text-slate-700">
            {user ? ROLE_LABELS[user.role] : 'an unknown role'}
          </span>
          . If you believe you should have access, contact your platform administrator.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Link to="/dashboard">
            <Button leftIcon={<LayoutDashboard className="h-4 w-4" />}>Go to Dashboard</Button>
          </Link>
          <button
            type="button"
            onClick={() => window.history.back()}
            className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100"
          >
            <ArrowLeft className="h-4 w-4" />
            Go back
          </button>
        </div>
      </div>
    </Layout>
  )
}
