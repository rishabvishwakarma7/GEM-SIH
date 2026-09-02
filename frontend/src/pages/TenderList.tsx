import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Plus, Search } from 'lucide-react'
import Layout from '../components/Layout'
import ProcessingStatusBadge from '../components/ProcessingStatusBadge'
import {
  PageHeader,
  Card,
  DataTable,
  FilterBar,
  Input,
  Select,
  Badge,
  Button,
  EmptyState,
  ErrorState,
} from '../components/ui'
import type { Column, Tone } from '../components/ui'
import { listTenders } from '../api/tenders'
import type { Tender, TenderStatus } from '../types'
import { useAuth } from '../context/AuthContext'
import { canManage } from '../lib/roles'
import { getErrorMessage } from '../lib/errors'
import { formatDate } from '../lib/format'

const TENDER_STATUS_META: Record<TenderStatus, { tone: Tone; label: string }> = {
  draft: { tone: 'neutral', label: 'Draft' },
  open: { tone: 'info', label: 'Open' },
  under_evaluation: { tone: 'warning', label: 'Under Evaluation' },
  closed: { tone: 'primary', label: 'Closed' },
}

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: '', label: 'All statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'open', label: 'Open' },
  { value: 'under_evaluation', label: 'Under Evaluation' },
  { value: 'closed', label: 'Closed' },
]

export default function TenderList() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [tenders, setTenders] = useState<Tender[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const load = useCallback(() => {
    setIsLoading(true)
    setError(null)
    listTenders()
      .then(setTenders)
      .catch((err) => setError(getErrorMessage(err, 'Failed to load tenders')))
      .finally(() => setIsLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return tenders.filter((t) => {
      if (statusFilter && t.status !== statusFilter) return false
      if (!q) return true
      return (
        t.tender_ref_no.toLowerCase().includes(q) ||
        t.title.toLowerCase().includes(q) ||
        (t.department ?? '').toLowerCase().includes(q) ||
        (t.organization ?? '').toLowerCase().includes(q)
      )
    })
  }, [tenders, search, statusFilter])

  const columns = useMemo<Column<Tender>[]>(
    () => [
      {
        key: 'tender_ref_no',
        header: 'Reference no.',
        render: (t) => (
          <span className="font-mono text-xs font-medium text-primary-700">{t.tender_ref_no}</span>
        ),
      },
      {
        key: 'title',
        header: 'Title',
        render: (t) => (
          <div className="min-w-0">
            <p className="font-medium text-slate-800">{t.title}</p>
            <p className="truncate text-xs text-slate-400">{t.department || t.organization}</p>
          </div>
        ),
      },
      {
        key: 'status',
        header: 'Status',
        render: (t) => {
          const meta = TENDER_STATUS_META[t.status]
          return (
            <Badge tone={meta.tone} size="sm">
              {meta.label}
            </Badge>
          )
        },
      },
      {
        key: 'processing_status',
        header: 'Processing',
        hideOnMobile: true,
        render: (t) => <ProcessingStatusBadge status={t.processing_status} />,
      },
      {
        key: 'created_at',
        header: 'Created',
        align: 'right',
        hideOnMobile: true,
        render: (t) => <span className="text-xs text-slate-500">{formatDate(t.created_at)}</span>,
      },
    ],
    [],
  )

  return (
    <Layout>
      <PageHeader
        icon={<FileText className="h-5 w-5" />}
        title="Tenders"
        description="Create tenders, upload tender documents, and review AI-extracted compliance requirements."
        breadcrumbs={[{ label: 'Tenders' }]}
        actions={
          canManage(user) ? (
            <Button leftIcon={<Plus className="h-4 w-4" />} onClick={() => navigate('/tenders/new')}>
              New tender
            </Button>
          ) : undefined
        }
      />

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <Card flush>
          <FilterBar
            search={
              <Input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search reference, title or department…"
                aria-label="Search tenders"
                leftIcon={<Search className="h-4 w-4" />}
              />
            }
          >
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter by status"
              className="w-44"
            >
              {STATUS_FILTERS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </Select>
          </FilterBar>

          <DataTable
            columns={columns}
            data={filtered}
            rowKey={(t) => t.id}
            onRowClick={(t) => navigate(`/tenders/${t.id}`)}
            loading={isLoading}
            skeletonRows={8}
            empty={
              <EmptyState
                icon={<FileText className="h-6 w-6" />}
                title={tenders.length === 0 ? 'No tenders yet' : 'No matching tenders'}
                description={
                  tenders.length === 0
                    ? canManage(user)
                      ? 'Create your first tender to get started.'
                      : 'Tenders will appear here once they are created.'
                    : 'No tenders match your search or filter.'
                }
                action={
                  tenders.length === 0 && canManage(user) ? (
                    <Button
                      size="sm"
                      leftIcon={<Plus className="h-4 w-4" />}
                      onClick={() => navigate('/tenders/new')}
                    >
                      New tender
                    </Button>
                  ) : undefined
                }
              />
            }
          />
        </Card>
      )}
    </Layout>
  )
}
