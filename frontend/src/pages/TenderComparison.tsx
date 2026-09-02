import { useEffect, useState, useMemo, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { BarChart3, Trophy, Building2, AlertTriangle, ArrowLeft, PlayCircle } from 'lucide-react'
import Layout from '../components/Layout'
import ComplianceStatusBadge from '../components/ComplianceStatusBadge'
import RiskBadge from '../components/RiskBadge'
import {
  PageHeader,
  SectionCard,
  DataTable,
  ScoreIndicator,
  Button,
  EmptyState,
  ErrorState,
  Alert,
} from '../components/ui'
import type { Column } from '../components/ui'
import { getTenderComparison, batchEvaluateTender } from '../api/compliance'
import type { BidderComparisonEntry, ComplianceStatus, RiskLevel } from '../types'
import { getErrorMessage } from '../lib/errors'
import { formatRelativeTime } from '../lib/format'
import { useAuth } from '../context/AuthContext'
import { canManage } from '../lib/roles'

const COMPLIANCE_STATUSES = new Set<string>(['compliant', 'non_compliant', 'needs_review'])
const RISK_LEVELS = new Set<string>(['low', 'medium', 'high'])

function rankClasses(rank: number): string {
  if (rank === 1) return 'bg-amber-100 text-amber-700 ring-1 ring-amber-200'
  if (rank === 2) return 'bg-slate-200 text-slate-600 ring-1 ring-slate-300'
  if (rank === 3) return 'bg-orange-100 text-orange-700 ring-1 ring-orange-200'
  return 'bg-slate-100 text-slate-500'
}

export default function TenderComparison() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const isManager = canManage(user)

  const [bidders, setBidders] = useState<BidderComparisonEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [isBatchRunning, setIsBatchRunning] = useState(false)
  const [batchError, setBatchError] = useState<string | null>(null)
  const [batchNotice, setBatchNotice] = useState<string | null>(null)

  const load = useCallback(() => {
    if (!id) return
    setIsLoading(true)
    setError(null)
    getTenderComparison(id)
      .then((data) => setBidders(data.bidders))
      .catch((err) => setError(getErrorMessage(err, 'Failed to load bidder comparison')))
      .finally(() => setIsLoading(false))
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  async function handleBatchRun() {
    if (!id) return
    setBatchError(null)
    setBatchNotice(null)
    setIsBatchRunning(true)
    try {
      const summary = await batchEvaluateTender(id)
      const failed = summary.results.filter((r) => !r.success)
      setBatchNotice(
        `Processed ${summary.bidders_processed} bidder(s)` +
          (failed.length ? ` — ${failed.length} failed (see server logs).` : '.'),
      )
      load()
    } catch (err) {
      setBatchError(getErrorMessage(err, 'Batch verification/evaluation failed.'))
    } finally {
      setIsBatchRunning(false)
    }
  }

  const columns = useMemo<Column<BidderComparisonEntry>[]>(
    () => [
      {
        key: 'rank',
        header: 'Rank',
        align: 'center',
        className: 'w-16',
        render: (_b, i) => (
          <span
            className={`inline-flex h-7 min-w-[1.75rem] items-center justify-center rounded-full px-2 text-xs font-bold ${rankClasses(
              i + 1,
            )}`}
          >
            {i + 1}
          </span>
        ),
      },
      {
        key: 'company_name',
        header: 'Bidder',
        render: (b) => (
          <div className="min-w-0">
            <p className="font-medium text-slate-800">{b.company_name}</p>
            {b.mandatory_failed && (
              <p className="mt-0.5 inline-flex items-center gap-1 text-xs font-medium text-danger-600">
                <AlertTriangle className="h-3.5 w-3.5" />
                Mandatory requirement failed
              </p>
            )}
          </div>
        ),
      },
      {
        key: 'compliance_score',
        header: 'Score',
        className: 'w-44',
        render: (b) => <ScoreIndicator score={b.compliance_score} variant="bar" />,
      },
      {
        key: 'overall_status',
        header: 'Final status',
        render: (b) =>
          COMPLIANCE_STATUSES.has(b.overall_status) ? (
            <ComplianceStatusBadge status={b.overall_status as ComplianceStatus} />
          ) : (
            <span className="text-slate-400">—</span>
          ),
      },
      {
        key: 'risk_level',
        header: 'Risk',
        hideOnMobile: true,
        render: (b) =>
          RISK_LEVELS.has(b.risk_level) ? (
            <RiskBadge level={b.risk_level as RiskLevel} />
          ) : (
            <span className="text-slate-400">—</span>
          ),
      },
      {
        key: 'breakdown',
        header: 'Breakdown',
        align: 'center',
        hideOnMobile: true,
        render: (b) => (
          <div className="flex items-center justify-center gap-3 text-xs font-medium tabular-nums">
            <span className="text-success-600" title="Compliant">
              ✓ {b.compliant_count}
            </span>
            <span className="text-danger-600" title="Non-compliant">
              ✕ {b.non_compliant_count}
            </span>
            <span className="text-warning-600" title="Needs review">
              ! {b.needs_review_count}
            </span>
            <span className="text-slate-400">/ {b.total_requirements}</span>
          </div>
        ),
      },
      {
        key: 'evaluated_at',
        header: 'Evaluated',
        align: 'right',
        hideOnMobile: true,
        render: (b) => (
          <span className="text-xs text-slate-500">{formatRelativeTime(b.evaluated_at)}</span>
        ),
      },
      // --- Upgrade: new intelligence columns ---
      {
        key: 'suspicious_document_count',
        header: 'Suspicious',
        align: 'center',
        hideOnMobile: true,
        render: (b) => (
          <span className={b.suspicious_document_count ? 'font-semibold text-orange-600' : 'text-slate-400'}>
            {b.suspicious_document_count ?? 0}
          </span>
        ),
      },
      {
        key: 'duplicate_document_count',
        header: 'Duplicates',
        align: 'center',
        hideOnMobile: true,
        render: (b) => (
          <span className={b.duplicate_document_count ? 'font-semibold text-yellow-600' : 'text-slate-400'}>
            {b.duplicate_document_count ?? 0}
          </span>
        ),
      },
      {
        key: 'document_completeness',
        header: 'Docs',
        align: 'center',
        hideOnMobile: true,
        render: (b) => (
          <span className="text-xs text-slate-600">
            {b.document_completeness !== undefined ? `${b.document_completeness}%` : '—'}
          </span>
        ),
      },
      {
        key: 'review_status',
        header: 'Review',
        hideOnMobile: true,
        render: (b) => b.review_status && b.review_status !== 'not_required' ? (
          <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
            b.review_status === 'closed' ? 'bg-slate-100 text-slate-500'
            : b.review_status === 'escalated' ? 'bg-red-100 text-red-700'
            : 'bg-purple-100 text-purple-700'
          }`}>
            {(b.review_status ?? '').replace('_', ' ')}
          </span>
        ) : <span className="text-slate-400 text-xs">—</span>,
      },
    ],
    [],
  )

  return (
    <Layout>
      <PageHeader
        icon={<BarChart3 className="h-5 w-5" />}
        title="Bidder comparison"
        description="AI-assisted compliance ranking — highest score first. Review flagged items before deciding."
        breadcrumbs={[
          { label: 'Tenders', to: '/tenders' },
          { label: 'Tender', to: id ? `/tenders/${id}` : '/tenders' },
          { label: 'Comparison' },
        ]}
        actions={
          id ? (
            <>
              {isManager && (
                <Button
                  variant="primary"
                  leftIcon={<PlayCircle className="h-4 w-4" />}
                  onClick={handleBatchRun}
                  loading={isBatchRunning}
                >
                  {isBatchRunning ? 'Running batch…' : 'Batch verify & evaluate all'}
                </Button>
              )}
              <Button
                variant="outline"
                leftIcon={<ArrowLeft className="h-4 w-4" />}
                onClick={() => navigate(`/tenders/${id}`)}
              >
                Back to tender
              </Button>
            </>
          ) : undefined
        }
      />

      {batchNotice && (
        <Alert variant="success" className="mb-4" onDismiss={() => setBatchNotice(null)}>
          {batchNotice}
        </Alert>
      )}
      {batchError && (
        <Alert variant="danger" className="mb-4" onDismiss={() => setBatchError(null)}>
          {batchError}
        </Alert>
      )}

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <SectionCard
          icon={<Trophy className="h-4 w-4" />}
          title="Compliance ranking"
          description="Ranked by overall compliance score across evaluated bidders."
          flush
        >
          <DataTable
            columns={columns}
            data={bidders}
            rowKey={(b) => b.bidder_id}
            onRowClick={(b) => navigate(`/bidders/${b.bidder_id}`)}
            loading={isLoading}
            skeletonRows={6}
            empty={
              <EmptyState
                icon={<Building2 className="h-6 w-6" />}
                title="No evaluated bidders yet"
                description="Run verification and compliance evaluation from a bidder's page to populate this comparison."
              />
            }
          />
        </SectionCard>
      )}
    </Layout>
  )
}
