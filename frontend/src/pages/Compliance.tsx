import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ShieldCheck, Search, Building2, Gauge, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react'
import Layout from '../components/Layout'
import {
  PageHeader,
  Card,
  StatCard,
  StatCardSkeleton,
  DataTable,
  FilterBar,
  Pagination,
  Input,
  Select,
  EmptyState,
  ErrorState,
  ScoreIndicator,
} from '../components/ui'
import type { Column } from '../components/ui'
import DashboardStatusPill from '../components/DashboardStatusPill'
import RiskBadge from '../components/RiskBadge'
import { getDashboardStats, getDashboardBidders } from '../api/dashboard'
import type { DashboardStats, DashboardBidderRow, RiskLevel } from '../types'
import { getErrorMessage } from '../lib/errors'
import { formatScore, formatRelativeTime } from '../lib/format'

const PAGE_SIZE = 10
const RISK_LEVELS: RiskLevel[] = ['low', 'medium', 'high']

type SortBy = 'company_name' | 'compliance_score' | 'status'

/**
 * Cross-tender compliance results explorer. Backed entirely by the real
 * /dashboard endpoints. Reads `search` and `status` from the URL so the global
 * search box and notification links deep-link straight into filtered results.
 */
export default function Compliance() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [statsError, setStatsError] = useState(false)

  const [search, setSearch] = useState(searchParams.get('search') ?? '')
  const [status, setStatus] = useState(searchParams.get('status') ?? '')
  const [sortBy, setSortBy] = useState<SortBy>('compliance_score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [page, setPage] = useState(1)

  const [rows, setRows] = useState<DashboardBidderRow[]>([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Adopt URL query params (top-bar search / notification deep links).
  useEffect(() => {
    setSearch(searchParams.get('search') ?? '')
    setStatus(searchParams.get('status') ?? '')
  }, [searchParams])

  // Debounce the free-text search before hitting the API.
  const [debouncedSearch, setDebouncedSearch] = useState(search)
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(t)
  }, [search])

  // Any filter/sort change resets to the first page.
  useEffect(() => {
    setPage(1)
  }, [debouncedSearch, status, sortBy, sortDir])

  useEffect(() => {
    let mounted = true
    getDashboardStats()
      .then((s) => mounted && setStats(s))
      .catch(() => mounted && setStatsError(true))
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)
    getDashboardBidders({
      search: debouncedSearch || undefined,
      status: status || undefined,
      sort_by: sortBy,
      sort_dir: sortDir,
      page,
      page_size: PAGE_SIZE,
    })
      .then((res) => {
        if (!mounted) return
        setRows(res.items)
        setTotal(res.total)
        setTotalPages(res.total_pages)
      })
      .catch((err) => mounted && setError(getErrorMessage(err)))
      .finally(() => mounted && setLoading(false))
    return () => {
      mounted = false
    }
  }, [debouncedSearch, status, sortBy, sortDir, page])

  function onSort(key: string) {
    const k = key as SortBy
    if (k === sortBy) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(k)
      setSortDir(k === 'company_name' ? 'asc' : 'desc')
    }
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
        key: 'tender_ref_no',
        header: 'Tender',
        hideOnMobile: true,
        render: (r) => <span className="font-mono text-xs text-slate-600">{r.tender_ref_no}</span>,
      },
      {
        key: 'compliance_score',
        header: 'Score',
        sortable: true,
        className: 'w-40',
        render: (r) =>
          r.compliance_score === null ? (
            <span className="text-sm text-slate-400">{formatScore(r.compliance_score)}</span>
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
        key: 'risk',
        header: 'Risk',
        hideOnMobile: true,
        render: (r) =>
          r.risk_level && RISK_LEVELS.includes(r.risk_level as RiskLevel) ? (
            <RiskBadge level={r.risk_level as RiskLevel} />
          ) : (
            <span className="text-sm text-slate-400">—</span>
          ),
      },
      {
        key: 'issues',
        header: 'Issues',
        align: 'center',
        hideOnMobile: true,
        render: (r) => (
          <div className="flex items-center justify-center gap-3 text-xs">
            <span
              className={r.failed_requirements > 0 ? 'font-semibold text-danger-600' : 'text-slate-400'}
              title="Failed requirements"
            >
              {r.failed_requirements} failed
            </span>
            <span
              className={r.review_items > 0 ? 'font-semibold text-warning-600' : 'text-slate-400'}
              title="Items needing review"
            >
              {r.review_items} review
            </span>
          </div>
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

  const statusOptions = [
    { value: '', label: 'All statuses' },
    { value: 'compliant', label: 'Compliant' },
    { value: 'needs_review', label: 'Needs Review' },
    { value: 'non_compliant', label: 'Non-Compliant' },
    { value: 'not_evaluated', label: 'Not Evaluated' },
  ]

  return (
    <Layout>
      <PageHeader
        icon={<ShieldCheck className="h-5 w-5" />}
        title="Compliance"
        description="Search and review compliance results for every bidder across all tenders."
        breadcrumbs={[{ label: 'Compliance' }]}
      />

      {/* Summary */}
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {!stats && !statsError ? (
          <StatCardSkeleton count={4} />
        ) : stats ? (
          <>
            <StatCard
              label="Avg. score"
              value={formatScore(stats.average_compliance_score)}
              icon={<Gauge className="h-5 w-5" />}
              tone="primary"
              hint={`${stats.evaluated_bidders} of ${stats.total_bidders} evaluated`}
            />
            <StatCard
              label="Compliant"
              value={stats.compliant_bidders}
              icon={<CheckCircle2 className="h-5 w-5" />}
              tone="success"
            />
            <StatCard
              label="Needs review"
              value={stats.needs_review_bidders}
              icon={<AlertTriangle className="h-5 w-5" />}
              tone="warning"
            />
            <StatCard
              label="Non-compliant"
              value={stats.non_compliant_bidders}
              icon={<XCircle className="h-5 w-5" />}
              tone="danger"
            />
          </>
        ) : null}
      </div>

      <Card flush>
        <FilterBar
          search={
            <Input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by company or GeM seller ID…"
              aria-label="Search bidders"
              leftIcon={<Search className="h-4 w-4" />}
            />
          }
        >
          <Select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            aria-label="Filter by status"
            className="w-44"
          >
            {statusOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </FilterBar>

        {error ? (
          <ErrorState message={error} onRetry={() => setPage((p) => p)} />
        ) : (
          <DataTable
            columns={columns}
            data={rows}
            rowKey={(r) => r.bidder_id}
            onRowClick={(r) => navigate(`/bidders/${r.bidder_id}`)}
            sortBy={sortBy}
            sortDir={sortDir}
            onSort={onSort}
            loading={loading}
            skeletonRows={PAGE_SIZE}
            empty={
              <EmptyState
                icon={<Building2 className="h-6 w-6" />}
                title="No bidders found"
                description={
                  debouncedSearch || status
                    ? 'No bidders match your filters. Try clearing the search or status filter.'
                    : 'Once bidders are added and evaluated, their compliance results appear here.'
                }
              />
            }
          />
        )}

        {!loading && !error && rows.length > 0 && (
          <Pagination
            page={page}
            totalPages={totalPages}
            total={total}
            pageSize={PAGE_SIZE}
            onPageChange={setPage}
          />
        )}
      </Card>
    </Layout>
  )
}
