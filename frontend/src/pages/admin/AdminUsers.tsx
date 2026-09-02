import { useEffect, useMemo, useState } from 'react'
import {
  Users as UsersIcon,
  UserPlus,
  Pencil,
  UserCheck,
  UserX,
  Search,
  ShieldCheck,
  Mail,
} from 'lucide-react'
import Layout from '../../components/Layout'
import {
  PageHeader,
  Card,
  Button,
  Badge,
  StatusBadge,
  DataTable,
  FilterBar,
  Input,
  Select,
  Modal,
  ConfirmDialog,
  Alert,
  EmptyState,
  ErrorState,
  FormField,
} from '../../components/ui'
import type { Column, Tone } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { ROLE_LABELS } from '../../lib/roles'
import { getErrorMessage } from '../../lib/errors'
import { formatDate } from '../../lib/format'
import { listUsers, createUser, updateUser } from '../../api/users'
import type { User, UserRole } from '../../types'

const ROLE_TONE: Record<UserRole, Tone> = {
  admin: 'navy',
  evaluator: 'primary',
  viewer: 'neutral',
}

const ROLE_OPTIONS: UserRole[] = ['admin', 'evaluator', 'viewer']

interface CreateForm {
  full_name: string
  email: string
  password: string
  role: UserRole
}

const EMPTY_FORM: CreateForm = { full_name: '', email: '', password: '', role: 'viewer' }

export default function AdminUsers() {
  const { user: currentUser } = useAuth()

  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [term, setTerm] = useState('')
  const [roleFilter, setRoleFilter] = useState('')

  const [notice, setNotice] = useState<{ tone: 'success' | 'danger'; msg: string } | null>(null)

  // Create modal
  const [createOpen, setCreateOpen] = useState(false)
  const [form, setForm] = useState<CreateForm>(EMPTY_FORM)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  // Edit modal
  const [editing, setEditing] = useState<User | null>(null)
  const [editName, setEditName] = useState('')
  const [editRole, setEditRole] = useState<UserRole>('viewer')
  const [savingEdit, setSavingEdit] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  // Activate / deactivate confirm
  const [confirmUser, setConfirmUser] = useState<User | null>(null)
  const [toggling, setToggling] = useState(false)

  async function refresh() {
    setLoading(true)
    setLoadError(null)
    try {
      setUsers(await listUsers())
    } catch (err) {
      setLoadError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  const activeAdminCount = useMemo(
    () => users.filter((u) => u.role === 'admin' && u.is_active).length,
    [users],
  )

  const filtered = useMemo(() => {
    const q = term.trim().toLowerCase()
    return users.filter((u) => {
      if (roleFilter && u.role !== roleFilter) return false
      if (!q) return true
      return (
        u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
      )
    })
  }, [users, term, roleFilter])

  function isSelf(u: User): boolean {
    return currentUser?.id === u.id
  }

  /** Last active admin cannot be deactivated or demoted (mirrors backend). */
  function isLastActiveAdmin(u: User): boolean {
    return u.role === 'admin' && u.is_active && activeAdminCount <= 1
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setCreateError(null)
    if (!form.full_name.trim()) return setCreateError('Full name is required.')
    if (!form.email.trim()) return setCreateError('Email is required.')
    if (form.password.length < 8) return setCreateError('Password must be at least 8 characters.')
    setCreating(true)
    try {
      await createUser({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
        role: form.role,
      })
      setCreateOpen(false)
      setForm(EMPTY_FORM)
      setNotice({ tone: 'success', msg: `User "${form.full_name.trim()}" created.` })
      await refresh()
    } catch (err) {
      setCreateError(getErrorMessage(err))
    } finally {
      setCreating(false)
    }
  }

  function openEdit(u: User) {
    setEditing(u)
    setEditName(u.full_name)
    setEditRole(u.role)
    setEditError(null)
  }

  async function handleEditSave(e: React.FormEvent) {
    e.preventDefault()
    if (!editing) return
    setEditError(null)
    const payload: { full_name?: string; role?: UserRole } = {}
    if (editName.trim() && editName.trim() !== editing.full_name) payload.full_name = editName.trim()
    if (!isSelf(editing) && editRole !== editing.role) payload.role = editRole
    if (Object.keys(payload).length === 0) {
      setEditing(null)
      return
    }
    setSavingEdit(true)
    try {
      await updateUser(editing.id, payload)
      setNotice({ tone: 'success', msg: `User "${editName.trim()}" updated.` })
      setEditing(null)
      await refresh()
    } catch (err) {
      setEditError(getErrorMessage(err))
    } finally {
      setSavingEdit(false)
    }
  }

  async function handleToggleActive() {
    if (!confirmUser) return
    setToggling(true)
    try {
      await updateUser(confirmUser.id, { is_active: !confirmUser.is_active })
      setNotice({
        tone: 'success',
        msg: `${confirmUser.full_name} ${confirmUser.is_active ? 'deactivated' : 'activated'}.`,
      })
      setConfirmUser(null)
      await refresh()
    } catch (err) {
      setNotice({ tone: 'danger', msg: getErrorMessage(err) })
      setConfirmUser(null)
    } finally {
      setToggling(false)
    }
  }

  const columns = useMemo<Column<User>[]>(
    () => [
      {
        key: 'name',
        header: 'User',
        render: (u) => (
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-slate-800">{u.full_name}</span>
              {isSelf(u) ? <Badge tone="primary" size="sm">You</Badge> : null}
            </div>
            <p className="truncate text-xs text-slate-400">{u.email}</p>
          </div>
        ),
      },
      {
        key: 'role',
        header: 'Role',
        render: (u) => <Badge tone={ROLE_TONE[u.role]}>{ROLE_LABELS[u.role]}</Badge>,
      },
      {
        key: 'status',
        header: 'Status',
        render: (u) =>
          u.is_active ? (
            <StatusBadge tone="success">Active</StatusBadge>
          ) : (
            <StatusBadge tone="neutral">Inactive</StatusBadge>
          ),
      },
      {
        key: 'created',
        header: 'Created',
        hideOnMobile: true,
        render: (u) => <span className="text-sm text-slate-500">{formatDate(u.created_at)}</span>,
      },
      {
        key: 'actions',
        header: '',
        align: 'right',
        render: (u) => {
          const lockToggle = isSelf(u) || isLastActiveAdmin(u)
          const toggleTitle = isSelf(u)
            ? 'You cannot deactivate your own account'
            : isLastActiveAdmin(u)
              ? 'At least one active administrator is required'
              : u.is_active
                ? 'Deactivate user'
                : 'Activate user'
          return (
            <div className="flex items-center justify-end gap-1.5">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => openEdit(u)}
                leftIcon={<Pencil className="h-3.5 w-3.5" />}
              >
                Edit
              </Button>
              <Button
                variant={u.is_active ? 'ghost' : 'outline'}
                size="sm"
                disabled={lockToggle}
                title={toggleTitle}
                onClick={() => setConfirmUser(u)}
                leftIcon={
                  u.is_active ? (
                    <UserX className="h-3.5 w-3.5" />
                  ) : (
                    <UserCheck className="h-3.5 w-3.5" />
                  )
                }
                className={u.is_active ? 'text-danger-600 hover:bg-danger-50' : undefined}
              >
                {u.is_active ? 'Deactivate' : 'Activate'}
              </Button>
            </div>
          )
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [currentUser, activeAdminCount],
  )

  return (
    <Layout>
      <PageHeader
        icon={<UsersIcon className="h-5 w-5" />}
        title="Users"
        description="Create accounts, assign roles and manage access to the platform."
        breadcrumbs={[{ label: 'Administration', to: '/admin' }, { label: 'Users' }]}
        actions={
          <Button leftIcon={<UserPlus className="h-4 w-4" />} onClick={() => setCreateOpen(true)}>
            Add user
          </Button>
        }
      />

      {notice && (
        <Alert variant={notice.tone} className="mb-4" onDismiss={() => setNotice(null)}>
          {notice.msg}
        </Alert>
      )}

      <Card flush>
        <FilterBar
          search={
            <Input
              type="search"
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              placeholder="Search by name or email…"
              aria-label="Search users"
              leftIcon={<Search className="h-4 w-4" />}
            />
          }
        >
          <Select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            aria-label="Filter by role"
            className="w-44"
          >
            <option value="">All roles</option>
            {ROLE_OPTIONS.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </Select>
        </FilterBar>

        {loadError ? (
          <ErrorState message={loadError} onRetry={refresh} />
        ) : (
          <DataTable
            columns={columns}
            data={filtered}
            rowKey={(u) => u.id}
            loading={loading}
            skeletonRows={6}
            empty={
              <EmptyState
                icon={<UsersIcon className="h-6 w-6" />}
                title="No users found"
                description={
                  term || roleFilter
                    ? 'No users match your filters.'
                    : 'Add your first user to get started.'
                }
              />
            }
          />
        )}
      </Card>

      {/* Create user */}
      <Modal
        open={createOpen}
        onClose={() => (creating ? undefined : setCreateOpen(false))}
        title="Add user"
        description="Create a new account and assign its role."
        icon={<UserPlus className="h-5 w-5" />}
        disableBackdropClose={creating}
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setCreateOpen(false)} disabled={creating}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleCreate} loading={creating}>
              Create user
            </Button>
          </>
        }
      >
        <form onSubmit={handleCreate} className="space-y-4">
          {createError && <Alert variant="danger">{createError}</Alert>}
          <FormField label="Full name" required>
            <Input
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              placeholder="e.g. Priya Sharma"
              autoFocus
            />
          </FormField>
          <FormField label="Email" required>
            <Input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="name@cpcl.gem"
              leftIcon={<Mail className="h-4 w-4" />}
            />
          </FormField>
          <FormField label="Temporary password" required hint="At least 8 characters. The user can change it later.">
            <Input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="••••••••"
            />
          </FormField>
          <FormField label="Role" required>
            <Select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
            >
              {ROLE_OPTIONS.map((r) => (
                <option key={r} value={r}>
                  {ROLE_LABELS[r]}
                </option>
              ))}
            </Select>
          </FormField>
        </form>
      </Modal>

      {/* Edit user */}
      <Modal
        open={!!editing}
        onClose={() => (savingEdit ? undefined : setEditing(null))}
        title="Edit user"
        icon={<Pencil className="h-5 w-5" />}
        disableBackdropClose={savingEdit}
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setEditing(null)} disabled={savingEdit}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleEditSave} loading={savingEdit}>
              Save changes
            </Button>
          </>
        }
      >
        {editing && (
          <form onSubmit={handleEditSave} className="space-y-4">
            {editError && <Alert variant="danger">{editError}</Alert>}
            <div className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
              <Mail className="mr-1.5 inline h-3.5 w-3.5 text-slate-400" />
              {editing.email}
            </div>
            <FormField label="Full name">
              <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
            </FormField>
            <FormField
              label="Role"
              hint={isSelf(editing) ? 'You cannot change your own role.' : undefined}
            >
              <Select
                value={editRole}
                onChange={(e) => setEditRole(e.target.value as UserRole)}
                disabled={isSelf(editing) || isLastActiveAdmin(editing)}
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r} value={r}>
                    {ROLE_LABELS[r]}
                  </option>
                ))}
              </Select>
            </FormField>
            {isLastActiveAdmin(editing) && !isSelf(editing) && (
              <p className="flex items-center gap-1.5 text-xs text-slate-500">
                <ShieldCheck className="h-3.5 w-3.5" />
                This is the last active administrator and cannot be demoted.
              </p>
            )}
          </form>
        )}
      </Modal>

      {/* Activate / deactivate confirm */}
      <ConfirmDialog
        open={!!confirmUser}
        title={confirmUser?.is_active ? 'Deactivate user?' : 'Activate user?'}
        tone={confirmUser?.is_active ? 'danger' : 'primary'}
        confirmLabel={confirmUser?.is_active ? 'Deactivate' : 'Activate'}
        loading={toggling}
        onCancel={() => setConfirmUser(null)}
        onConfirm={handleToggleActive}
        message={
          confirmUser?.is_active
            ? `${confirmUser?.full_name} will immediately lose access and will be signed out. You can reactivate them later.`
            : `${confirmUser?.full_name} will regain access to the platform.`
        }
      />
    </Layout>
  )
}
