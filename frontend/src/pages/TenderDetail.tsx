import { useEffect, useRef, useState, useCallback, useMemo, type ChangeEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  FileText,
  Sparkles,
  Users,
  ListChecks,
  Building2,
  RefreshCw,
  FileCheck2,
  ArrowRight,
  ScrollText,
} from 'lucide-react'
import Layout from '../components/Layout'
import ProcessingStatusBadge from '../components/ProcessingStatusBadge'
import ConfidenceIndicator from '../components/ConfidenceIndicator'
import RequirementDetailModal from '../components/RequirementDetailModal'
import {
  PageHeader,
  SectionCard,
  Tabs,
  DataTable,
  FilterBar,
  Select,
  Button,
  Badge,
  StatCard,
  EmptyState,
  ErrorState,
  Alert,
  Progress,
  Spinner,
} from '../components/ui'
import type { Column, TabItem } from '../components/ui'
import {
  getTender,
  uploadTenderDocument,
  processTender,
  getTenderStatus,
  listTenderRequirements,
} from '../api/tenders'
import type { TenderDetail as TenderDetailType, TenderRequirement } from '../types'
import { REQUIREMENT_CATEGORY_LABELS } from '../types'
import { useAuth } from '../context/AuthContext'
import { canManage as canManageRole } from '../lib/roles'

const POLLING_STATUSES = new Set(['extracting_text', 'extracting_requirements'])

type TabKey = 'requirements' | 'document' | 'bidders'

export default function TenderDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const canManage = canManageRole(user)

  const [tender, setTender] = useState<TenderDetailType | null>(null)
  const [requirements, setRequirements] = useState<TenderRequirement[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [selectedRequirement, setSelectedRequirement] = useState<TenderRequirement | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [reviewOnly, setReviewOnly] = useState(false)
  const [activeTab, setActiveTab] = useState<TabKey>('requirements')

  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<number | null>(null)

  const loadTender = useCallback(async () => {
    if (!id) return
    try {
      const data = await getTender(id)
      setTender(data)
      const reqs = await listTenderRequirements(id)
      setRequirements(reqs)
      return data
    } catch {
      setError('Failed to load tender')
      return null
    }
  }, [id])

  useEffect(() => {
    loadTender().finally(() => setIsLoading(false))
  }, [loadTender])

  // Poll status while the AI pipeline is running
  useEffect(() => {
    if (!id || !tender) return

    if (POLLING_STATUSES.has(tender.processing_status)) {
      pollRef.current = window.setInterval(async () => {
        const status = await getTenderStatus(id)
        setTender((prev) => (prev ? { ...prev, ...status } : prev))
        if (!POLLING_STATUSES.has(status.processing_status)) {
          if (pollRef.current) window.clearInterval(pollRef.current)
          const reqs = await listTenderRequirements(id)
          setRequirements(reqs)
        }
      }, 2500)
    }

    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current)
    }
  }, [id, tender?.processing_status])

  async function handleFileSelected(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !id) return
    setActionError(null)
    setUploadProgress(0)
    try {
      await uploadTenderDocument(id, file, setUploadProgress)
      await loadTender()
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || 'Upload failed')
    } finally {
      setUploadProgress(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleProcess() {
    if (!id) return
    setActionError(null)
    try {
      const status = await processTender(id)
      setTender((prev) => (prev ? { ...prev, ...status } : prev))
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || 'Failed to start processing')
    }
  }

  const filteredRequirements = useMemo(
    () =>
      requirements.filter((r) => {
        if (categoryFilter !== 'all' && r.category !== categoryFilter) return false
        if (reviewOnly && !r.needs_review) return false
        return true
      }),
    [requirements, categoryFilter, reviewOnly],
  )

  const categories = useMemo(
    () => Array.from(new Set(requirements.map((r) => r.category))),
    [requirements],
  )

  const columns = useMemo<Column<TenderRequirement>[]>(
    () => [
      {
        key: 'category',
        header: 'Category',
        render: (r) => (
          <Badge tone="neutral" size="sm">
            {REQUIREMENT_CATEGORY_LABELS[r.category]}
          </Badge>
        ),
      },
      {
        key: 'title',
        header: 'Requirement',
        render: (r) => (
          <div className="min-w-0">
            <p className="font-medium text-slate-800">{r.title}</p>
            {r.clause_reference ? (
              <p className="truncate text-xs text-slate-400">Clause {r.clause_reference}</p>
            ) : null}
          </div>
        ),
      },
      {
        key: 'mandatory',
        header: 'Mandatory',
        align: 'center',
        render: (r) =>
          r.mandatory ? (
            <Badge tone="danger" size="sm">
              Mandatory
            </Badge>
          ) : (
            <Badge tone="neutral" size="sm">
              Optional
            </Badge>
          ),
      },
      {
        key: 'verification_type',
        header: 'Verification',
        hideOnMobile: true,
        render: (r) => (
          <span className="text-xs capitalize text-slate-500">
            {r.verification_type.replace(/_/g, ' ')}
          </span>
        ),
      },
      {
        key: 'page_number',
        header: 'Page',
        align: 'center',
        hideOnMobile: true,
        render: (r) => <span className="text-xs text-slate-500">{r.page_number ?? '—'}</span>,
      },
      {
        key: 'confidence',
        header: 'Confidence',
        render: (r) => (
          <ConfidenceIndicator confidence={r.confidence} needsReview={r.needs_review} />
        ),
      },
    ],
    [],
  )

  if (isLoading) {
    return (
      <Layout>
        <div className="mt-16 flex justify-center">
          <Spinner size={28} label="Loading tender…" />
        </div>
      </Layout>
    )
  }

  if (error || !tender) {
    return (
      <Layout>
        <PageHeader
          icon={<FileText className="h-5 w-5" />}
          title="Tender"
          breadcrumbs={[{ label: 'Tenders', to: '/tenders' }, { label: 'Tender' }]}
        />
        <ErrorState
          message={error || 'Tender not found.'}
          onRetry={
            error
              ? () => {
                  setError(null)
                  setIsLoading(true)
                  loadTender().finally(() => setIsLoading(false))
                }
              : undefined
          }
        />
      </Layout>
    )
  }

  const isBusy = POLLING_STATUSES.has(tender.processing_status)
  const mandatoryCount = requirements.filter((r) => r.mandatory).length
  const reviewCount = requirements.filter((r) => r.needs_review).length

  const tabs: TabItem[] = [
    {
      key: 'requirements',
      label: 'Requirements',
      icon: <ListChecks className="h-4 w-4" />,
      count: requirements.length,
    },
    { key: 'document', label: 'Document', icon: <FileText className="h-4 w-4" /> },
    { key: 'bidders', label: 'Bidders', icon: <Users className="h-4 w-4" /> },
  ]

  return (
    <Layout>
      <PageHeader
        icon={<FileText className="h-5 w-5" />}
        title={tender.title}
        description={`${tender.tender_ref_no} · ${tender.department || tender.organization}`}
        breadcrumbs={[{ label: 'Tenders', to: '/tenders' }, { label: tender.tender_ref_no }]}
        actions={<ProcessingStatusBadge status={tender.processing_status} />}
      />

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Requirements"
          value={requirements.length}
          icon={<ListChecks className="h-5 w-5" />}
          tone="navy"
        />
        <StatCard
          label="Mandatory"
          value={mandatoryCount}
          icon={<ScrollText className="h-5 w-5" />}
          tone="primary"
        />
        <StatCard
          label="Needs review"
          value={reviewCount}
          icon={<Sparkles className="h-5 w-5" />}
          tone={reviewCount > 0 ? 'warning' : 'neutral'}
          hint={reviewCount > 0 ? 'Low-confidence AI extractions' : 'All high-confidence'}
        />
        <StatCard
          label="Pages"
          value={tender.page_count ?? '—'}
          icon={<FileText className="h-5 w-5" />}
          tone="neutral"
        />
      </div>

      <Tabs
        tabs={tabs}
        active={activeTab}
        onChange={(k) => setActiveTab(k as TabKey)}
        className="mb-6"
      />

      {activeTab === 'requirements' && (
        <SectionCard
          icon={<ListChecks className="h-4 w-4" />}
          title="AI-extracted requirements"
          description="AI-assisted extraction. Confidence is shown per row — verify flagged items before relying on them."
          flush
        >
          <FilterBar>
            <Select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              aria-label="Filter by category"
              className="w-52"
            >
              <option value="all">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {REQUIREMENT_CATEGORY_LABELS[c]}
                </option>
              ))}
            </Select>
            <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={reviewOnly}
                onChange={(e) => setReviewOnly(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-2 focus:ring-primary-500/30"
              />
              Needs review only
            </label>
          </FilterBar>

          <DataTable
            columns={columns}
            data={filteredRequirements}
            rowKey={(r) => r.id}
            onRowClick={(r) => setSelectedRequirement(r)}
            empty={
              <EmptyState
                icon={<ListChecks className="h-6 w-6" />}
                title={
                  requirements.length === 0 ? 'No requirements yet' : 'No matching requirements'
                }
                description={
                  requirements.length === 0
                    ? tender.processing_status === 'completed'
                      ? 'No compliance requirements were identified in this document.'
                      : 'Upload a document and run AI extraction to populate requirements.'
                    : 'No requirements match the current filters.'
                }
              />
            }
          />
        </SectionCard>
      )}

      {activeTab === 'document' && (
        <SectionCard
          icon={<FileText className="h-4 w-4" />}
          title="Tender document"
          description="Upload the tender PDF, then run AI-assisted extraction to identify compliance requirements."
        >
          <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
            {tender.document_path ? (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
                <span className="inline-flex items-center gap-2 font-medium text-success-700">
                  <FileCheck2 className="h-4 w-4" /> Document uploaded
                </span>
                {tender.page_count ? (
                  <Badge tone="neutral" size="sm">
                    {tender.page_count} page{tender.page_count === 1 ? '' : 's'}
                  </Badge>
                ) : null}
                {tender.extraction_method ? (
                  <Badge tone="info" size="sm">
                    Extracted via {tender.extraction_method.toUpperCase()}
                  </Badge>
                ) : null}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No document uploaded yet.</p>
            )}
          </div>

          {isBusy && (
            <Alert variant="info" className="mt-4" title="AI extraction in progress">
              {tender.processing_status === 'extracting_text'
                ? 'Extracting text from the PDF. OCR fallback runs automatically for scanned documents…'
                : 'Analyzing the tender and identifying compliance requirements…'}
            </Alert>
          )}

          {tender.processing_status === 'failed' && tender.processing_error && (
            <Alert variant="danger" className="mt-4" title="Processing failed">
              {tender.processing_error}
            </Alert>
          )}

          {canManage ? (
            <div className="mt-4 space-y-4">
              {actionError && (
                <Alert variant="danger" onDismiss={() => setActionError(null)}>
                  {actionError}
                </Alert>
              )}
              <div className="flex flex-wrap items-center gap-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf"
                  onChange={handleFileSelected}
                  disabled={uploadProgress !== null || isBusy}
                  className="text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-primary-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-primary-700 hover:file:bg-primary-100 disabled:opacity-60"
                />
                {tender.document_path && !isBusy && (
                  <Button
                    onClick={handleProcess}
                    leftIcon={
                      tender.processing_status === 'completed' ? (
                        <RefreshCw className="h-4 w-4" />
                      ) : (
                        <Sparkles className="h-4 w-4" />
                      )
                    }
                  >
                    {tender.processing_status === 'completed'
                      ? 'Re-run AI extraction'
                      : 'Run AI extraction'}
                  </Button>
                )}
              </div>
              {uploadProgress !== null && (
                <div>
                  <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                    <span>Uploading…</span>
                    <span className="tabular-nums">{uploadProgress}%</span>
                  </div>
                  <Progress value={uploadProgress} />
                </div>
              )}
              <p className="text-xs text-slate-400">
                AI-assisted extraction can miss or misread clauses. Review flagged requirements
                before relying on them.
              </p>
            </div>
          ) : (
            <p className="mt-4 text-xs text-slate-400">
              You have read-only access. Ask an evaluator or administrator to upload documents or run
              extraction.
            </p>
          )}
        </SectionCard>
      )}

      {activeTab === 'bidders' && (
        <SectionCard
          icon={<Users className="h-4 w-4" />}
          title="Bidders"
          description="Manage bidders for this tender, upload eligibility documents, and review AI-extracted data and consistency checks."
        >
          <div className="flex flex-wrap gap-3">
            <Button
              variant="outline"
              leftIcon={<Users className="h-4 w-4" />}
              onClick={() => navigate(`/bidders?tender_id=${tender.id}`)}
            >
              View bidders
            </Button>
            <Button
              variant="outline"
              leftIcon={<Building2 className="h-4 w-4" />}
              onClick={() => navigate(`/tenders/${tender.id}/comparison`)}
            >
              Compliance comparison
            </Button>
            {canManage && (
              <Button
                leftIcon={<ArrowRight className="h-4 w-4" />}
                onClick={() => navigate(`/bidders/new?tender_id=${tender.id}`)}
              >
                Add bidder
              </Button>
            )}
          </div>
        </SectionCard>
      )}

      {selectedRequirement && (
        <RequirementDetailModal
          requirement={selectedRequirement}
          onClose={() => setSelectedRequirement(null)}
        />
      )}
    </Layout>
  )
}
