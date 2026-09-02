import { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  FileText,
  Building2,
  Gauge,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Search,
  Plus,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import Layout from '../components/Layout'
import {
  PageHeader,
  StatCard,
  StatCardSkeleton,
  SectionCard,
  DataTable,
  FilterBar,
  Pagination,
  Input,
  Select,
  EmptyState,
  ErrorState,
  ScoreIndicator,
  Button,
} from '../components/ui'
import type { Column } from '../components/ui'
import DashboardStatusPill from '../components/DashboardStatusPill'
import { getDashboardStats, getDashboardBidders } from '../api/dashboard'
import type { DashboardStats, DashboardBidderRow } from '../types'
import { canManage } from '../lib/roles'
import { getErrorMessage } from '../lib/errors'
import { formatScore, formatRelativeTime } from '../lib/format'

const STATUS_FILTERS = [
  { value: '', label: 'All statuses' },
  { value: 'compliant', label: 'Compliant' },
  { value: 'non_compliant', label: 'Non-Compliant' },
  { value: 'needs_review', label: 'Needs Review' },
  { value: 'not_evaluated', label: 'Not Evaluated' },
]

const PAGE_SIZE = 10

type SortBy = 'company_name' | 'compliance_score' | 'status'

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)
  const [statsError, setStatsError] = useState<string | null>(null)

  const [rows, setRows] = useState<DashboardBidderRow[]>([])
  const [tableLoading, setTableLoading] = useState(true)
  const [tableError, setTableError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)

  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState<SortBy>('company_name')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [page, setPage] = useState(1)

  const loadStats = useCallback(() => {
    setStatsLoading(true)
    setStatsError(null)
    getDashboardStats()
      .then(setStats)
      .catch((err) => setStatsError(getErrorMessage(err)))
      .finally(() => setStatsLoading(false))
  }, [])

  useEffect(() => {
    loadStats()
  }, [loadStats])

  const loadTable = useCallback(() => {
    setTableLoading(true)
    setTableError(null)
    getDashboardBidders({
      search: search || undefined,
      status: statusFilter || undefined,
      sort_by: sortBy,
      sort_dir: sortDir,
      page,
      page_size: PAGE_SIZE,
    })
      .then((data) => {
        setRows(data.items)
        setTotal(data.total)
        setTotalPages(data.total_pages)
      })
      .catch((err) => setTableError(getErrorMessage(err)))
      .finally(() => setTableLoading(false))
  }, [search, statusFilter, sortBy, sortDir, page])

  useEffect(() => {
    loadTable()
  }, [loadTable])

  // Debounce the search box, resetting to the first page on change.
  useEffect(() => {
    const t = window.setTimeout(() => {
      setSearch(searchInput)
      setPage(1)
    }, 350)
    return () => window.clearTimeout(t)
  }, [searchInput])

  function handleSort(col: string) {
    const k = col as SortBy
    if (sortBy === k) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(k)
      setSortDir(k === 'company_name' ? 'asc' : 'desc')
    }
    setPage(1)
  }

  const columns = useMemo<Column<DashboardBidderRow>[]>(
    () => [
      {
        key: 'company_name',
        header: 'Bidder',
        sortable: true,
        render: (r) => (
          <div className="min-w-0">
            <p className="font-medium text-slate-800">{r.company_name}</p>
            <p className="truncate text-xs text-slate-400">
              {r.gem_seller_id ? `GeM: ${r.gem_seller_id}` : r.tender_ref_no}
            </p>
          </div>
        ),
      },
      {
        key: 'compliance_score',
        header: 'Score',
        sortable: true,
        className: 'w-40',
        render: (r) =>
          r.compliance_score === null ? (
            <span className="text-sm text-slate-400">—</span>
          ) : (
            <ScoreIndicator score={r.compliance_score} variant="bar" />
          ),
      },
      {
        key: 'status',
        header: 'Status',
        sortable: true,
        render: (r) => <DashboardStatusPill status={r.status} />,
      },
      {
        key: 'failed_requirements',
        header: 'Failed',
        align: 'center',
        hideOnMobile: true,
        render: (r) => (
          <span
            className={
              r.failed_requirements > 0 ? 'font-semibold text-danger-600' : 'text-slate-400'
            }
          >
            {r.failed_requirements}
          </span>
        ),
      },
      {
        key: 'review_items',
        header: 'Review',
        align: 'center',
        hideOnMobile: true,
        render: (r) => (
          <span className={r.review_items > 0 ? 'font-semibold text-warning-600' : 'text-slate-400'}>
            {r.review_items}
          </span>
        ),
      },
      {
        key: 'evaluated_at',
        header: 'Evaluated',
        align: 'right',
        hideOnMobile: true,
        render: (r) => (
          <span className="text-xs text-slate-500">{formatRelativeTime(r.evaluated_at)}</span>
        ),
      },
    ],
    [],
  )

  return (
    <Layout>
      <PageHeader
        icon={<LayoutDashboard className="h-5 w-5" />}
        title={user?.full_name ? `Welcome, ${user.full_name.split(' ')[0]}` : 'Dashboard'}
        description="Live rollup of tenders, bidders and compliance verification across the platform."
        breadcrumbs={[{ label: 'Dashboard' }]}
        actions={
          canManage(user) ? (
            <Button leftIcon={<Plus className="h-4 w-4" />} onClick={() => navigate('/tenders/new')}>
              New tender
            </Button>
          ) : undefined
        }
      />

      {/* Summary metrics */}
      {statsError ? (
        <ErrorState message={statsError} onRetry={loadStats} compact />
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          {statsLoading || !stats ? (
            <StatCardSkeleton count={6} />
          ) : (
            <>
              <StatCard
                label="Tenders"
                value={stats.total_tenders}
                icon={<FileText className="h-5 w-5" />}
                tone="navy"
                to="/tenders"
              />
              <StatCard
                label="Bidders"
                value={stats.total_bidders}
                icon={<Building2 className="h-5 w-5" />}
                tone="primary"
                to="/bidders"
              />
              <StatCard
                label="Avg. score"
                value={formatScore(stats.average_compliance_score)}
                icon={<Gauge className="h-5 w-5" />}
                tone="primary"
                hint={`${stats.evaluated_bidders}/${stats.total_bidders} evaluated`}
              />
              <StatCard
                label="Compliant"
                value={stats.compliant_bidders}
                icon={<CheckCircle2 className="h-5 w-5" />}
                tone="success"
                to="/compliance?status=compliant"
              />
              <StatCard
                label="Needs review"
                value={stats.needs_review_bidders}
                icon={<AlertTriangle className="h-5 w-5" />}
                tone="warning"
                to="/compliance?status=needs_review"
              />
              <StatCard
                label="Non-compliant"
                value={stats.non_compliant_bidders}
                icon={<XCircle className="h-5 w-5" />}
                tone="danger"
                to="/compliance?status=non_compliant"
              />
            </>
          )}
        </div>
      )}

      {/* Bidder table */}
      <div className="mt-6">
        <SectionCard title="All bidders" description="Every bidder across all tenders." bodyClassName="p-0">
          <div className="px-4 pt-4">
            <FilterBar
              search={
                <Input
                  type="search"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search company or GeM seller ID…"
                  aria-label="Search bidders"
                  leftIcon={<Search className="h-4 w-4" />}
                />
              }
            >
              <Select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value)
                  setPage(1)
                }}
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
          </div>

          {tableError ? (
            <div className="p-4">
              <ErrorState message={tableError} onRetry={loadTable} />
            </div>
          ) : (
            <DataTable
              columns={columns}
              data={rows}
              rowKey={(r) => r.bidder_id}
              onRowClick={(r) => navigate(`/bidders/${r.bidder_id}`)}
              sortBy={sortBy}
              sortDir={sortDir}
              onSort={handleSort}
              loading={tableLoading}
              skeletonRows={PAGE_SIZE}
              empty={
                <EmptyState
                  icon={<Building2 className="h-6 w-6" />}
                  title="No bidders found"
                  description={
                    search || statusFilter
                      ? 'No bidders match your search or filter.'
                      : 'Create a tender and add bidders to get started.'
                  }
                />
              }
            />
          )}

          {!tableLoading && !tableError && rows.length > 0 && (
            <Pagination
              page={page}
              totalPages={totalPages}
              total={total}
              pageSize={PAGE_SIZE}
              onPageChange={setPage}
            />
          )}
        </SectionCard>
      </div>
    </Layout>
  )
}
