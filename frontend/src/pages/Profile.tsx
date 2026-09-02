import { useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { UserCircle, Lock, Eye, EyeOff, ShieldCheck, KeyRound } from 'lucide-react'
import Layout from '../components/Layout'
import {
  PageHeader,
  SectionCard,
  FormField,
  Input,
  Button,
  Alert,
  Badge,
  Spinner,
} from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { changeOwnPassword } from '../api/users'
import { ROLE_LABELS } from '../lib/roles'
import { getErrorMessage } from '../lib/errors'
import { formatDate } from '../lib/format'

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="text-sm font-medium text-slate-800">{children}</dd>
    </div>
  )
}

function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete,
  minLength,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  autoComplete: string
  minLength?: number
}) {
  const [show, setShow] = useState(false)
  return (
    <FormField label={label} htmlFor={id} required>
      <div className="relative">
        <Input
          id={id}
          type={show ? 'text' : 'password'}
          autoComplete={autoComplete}
          required
          minLength={minLength}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          leftIcon={<Lock className="h-4 w-4" />}
          className="pr-10"
        />
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 transition-colors hover:text-slate-600 focus-visible:text-primary-600 focus:outline-none"
          aria-label={show ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          tabIndex={-1}
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </FormField>
  )
}

export default function Profile() {
  const { user } = useAuth()

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(false)

    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.')
      return
    }

    setIsSaving(true)
    try {
      await changeOwnPassword(currentPassword, newPassword)
      setSuccess(true)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to change password'))
    } finally {
      setIsSaving(false)
    }
  }

  if (!user) {
    return (
      <Layout>
        <PageHeader
          icon={<UserCircle className="h-5 w-5" />}
          title="Your profile"
          breadcrumbs={[{ label: 'Profile' }]}
        />
        <div className="mt-16 flex justify-center">
          <Spinner size={28} label="Loading profile…" />
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageHeader
        icon={<UserCircle className="h-5 w-5" />}
        title="Your profile"
        description="Your account details and security settings."
        breadcrumbs={[{ label: 'Profile' }]}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SectionCard icon={<ShieldCheck className="h-4 w-4" />} title="Account">
          <dl className="divide-y divide-slate-100">
            <Row label="Full name">{user.full_name}</Row>
            <Row label="Email">
              <span className="font-normal text-slate-600">{user.email}</span>
            </Row>
            <Row label="Role">
              <Badge tone="navy">{ROLE_LABELS[user.role]}</Badge>
            </Row>
            <Row label="Account created">{formatDate(user.created_at)}</Row>
          </dl>
        </SectionCard>

        <SectionCard
          icon={<KeyRound className="h-4 w-4" />}
          title="Change password"
          description="Use at least 6 characters. You'll stay signed in after changing it."
        >
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            {success && (
              <Alert variant="success" onDismiss={() => setSuccess(false)}>
                Password changed successfully.
              </Alert>
            )}
            {error && (
              <Alert variant="danger" onDismiss={() => setError(null)}>
                {error}
              </Alert>
            )}

            <PasswordField
              id="current_password"
              label="Current password"
              value={currentPassword}
              onChange={setCurrentPassword}
              autoComplete="current-password"
            />
            <PasswordField
              id="new_password"
              label="New password"
              value={newPassword}
              onChange={setNewPassword}
              autoComplete="new-password"
              minLength={6}
            />
            <PasswordField
              id="confirm_password"
              label="Confirm new password"
              value={confirmPassword}
              onChange={setConfirmPassword}
              autoComplete="new-password"
              minLength={6}
            />

            <div className="flex justify-end border-t border-slate-100 pt-5">
              <Button type="submit" loading={isSaving} leftIcon={<KeyRound className="h-4 w-4" />}>
                {isSaving ? 'Saving…' : 'Change password'}
              </Button>
            </div>
          </form>
        </SectionCard>
      </div>
    </Layout>
  )
}
