import { useState, FormEvent } from 'react'
import { useNavigate, useLocation, Navigate } from 'react-router-dom'
import {
  ShieldCheck,
  Mail,
  Lock,
  Eye,
  EyeOff,
  CheckCircle2,
  FileCheck2,
  ScanSearch,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { Button, Input, FormField, Alert, Spinner } from '../components/ui'
import { getErrorMessage } from '../lib/errors'

const HIGHLIGHTS = [
  { icon: ScanSearch, text: 'AI-assisted extraction of tender requirements & bidder documents' },
  { icon: FileCheck2, text: 'Automated compliance scoring with human-in-the-loop review' },
  { icon: ShieldCheck, text: 'Role-based access with a complete, read-only audit trail' },
]

export default function Login() {
  const [email, setEmail] = useState('admin@cpcl.gem')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { login, isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/dashboard'

  // Already signed in → skip the login screen.
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <Spinner size={28} label="Loading…" />
      </div>
    )
  }
  if (isAuthenticated) return <Navigate to={from} replace />

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Login failed. Please check your credentials and try again.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Brand panel */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-sidebar-gradient p-12 text-white lg:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'radial-gradient(circle at 25% 20%, white 1px, transparent 1px), radial-gradient(circle at 75% 65%, white 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
          aria-hidden="true"
        />
        <div className="relative flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/20 backdrop-blur">
            <ShieldCheck className="h-6 w-6" />
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold tracking-wide">CPCL · GeM Procurement</p>
            <p className="text-xs text-white/60">Chennai Petroleum Corporation Limited</p>
          </div>
        </div>

        <div className="relative max-w-md">
          <h1 className="text-3xl font-bold leading-tight">Bid Compliance Verification Platform</h1>
          <p className="mt-4 text-sm leading-relaxed text-white/70">
            Verify GeM bidder submissions against tender requirements — faster, more consistently,
            and with a defensible record of every decision.
          </p>
          <ul className="mt-8 space-y-4">
            {HIGHLIGHTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-3">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/10 ring-1 ring-white/15">
                  <Icon className="h-4 w-4" />
                </span>
                <span className="text-sm text-white/85">{text}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/50">
          Smart India Hackathon 2026 · Problem Statement PS 26100 · MoP&amp;NG
        </p>
      </div>

      {/* Form panel */}
      <div className="flex w-full flex-col justify-center px-6 py-12 sm:px-12 lg:w-1/2">
        <div className="mx-auto w-full max-w-sm">
          {/* Compact brand for small screens */}
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy-800 text-white">
              <ShieldCheck className="h-5 w-5" />
            </span>
            <div className="leading-tight">
              <p className="text-sm font-semibold text-slate-800">CPCL · GeM Procurement</p>
              <p className="text-xs text-slate-500">Bid Compliance Platform</p>
            </div>
          </div>

          <h2 className="text-2xl font-bold text-slate-900">Sign in</h2>
          <p className="mt-1 text-sm text-slate-500">
            Use your official credentials to access the platform.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5" noValidate>
            {error && <Alert variant="danger">{error}</Alert>}

            <FormField label="Email address" htmlFor="email" required>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@cpcl.gem"
                leftIcon={<Mail className="h-4 w-4" />}
                invalid={!!error}
              />
            </FormField>

            <FormField label="Password" htmlFor="password" required>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  leftIcon={<Lock className="h-4 w-4" />}
                  invalid={!!error}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 transition-colors hover:text-slate-600 focus:outline-none focus-visible:text-primary-600"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </FormField>

            <Button type="submit" className="w-full" size="lg" loading={isSubmitting}>
              {isSubmitting ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>

          <div className="mt-8 flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs text-slate-500">
            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
            <span>
              Demo access · <span className="font-mono text-slate-600">admin@cpcl.gem</span> /{' '}
              <span className="font-mono text-slate-600">Admin@123</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
