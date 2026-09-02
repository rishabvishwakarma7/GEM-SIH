import { useEffect, useRef, useState, useCallback, useMemo, type ChangeEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Building2,
  FileText,
  FileCheck2,
  FileX2,
  AlertTriangle,
  FileBarChart,
  RotateCw,
  UploadCloud,
  ShieldAlert,
  Link2,
  Gavel,
  Clock,
} from 'lucide-react'
import Layout from '../components/Layout'
import DocumentProcessingStatusBadge from '../components/DocumentProcessingStatusBadge'
import BidderConsistencyStatusBadge from '../components/BidderConsistencyStatusBadge'
import BidderConsistencyPanel from '../components/BidderConsistencyPanel'
import BidderDocumentDetailModal from '../components/BidderDocumentDetailModal'
import ConfidenceIndicator from '../components/ConfidenceIndicator'
import ComplianceDashboardPanel from '../components/ComplianceDashboardPanel'
import WhyRiskyPanel from '../components/WhyRiskyPanel'
import EvidenceTrailPanel from '../components/EvidenceTrailPanel'
import FinalDecisionPanel from '../components/FinalDecisionPanel'
import RiskTimeline from '../components/RiskTimeline'
import RiskScoreCard from '../components/RiskScoreCard'
import {
  PageHeader,
  StatCard,
  StatCardSkeleton,
  SectionCard,
  DataTable,
  Button,
  Alert,
  Badge,
  Progress,
  Select,
  FormField,
  EmptyState,
  ErrorState,
  Spinner,
} from '../components/ui'
import type { Column } from '../components/ui'
import { getBidder, analyzeBidder } from '../api/bidders'
import { uploadBidderDocument, processBidderDocument } from '../api/documents'
import type {
  BidderDetail as BidderDetailType,
  BidderDocumentDetail,
  BidderDocumentType,
} from '../types'
import { BIDDER_DOCUMENT_TYPE_LABELS } from '../types'
import { useAuth } from '../context/AuthContext'
import { canManage } from '../lib/roles'
import { getErrorMessage } from '../lib/errors'

const POLLING_DOC_STATUSES = new Set(['extracting_text', 'extracting_data'])

const DOCUMENT_TYPE_OPTIONS = Object.entries(BIDDER_DOCUMENT_TYPE_LABELS) as [
  BidderDocumentType,
  string,
][]

export default function BidderDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const isManager = canManage(user)

  const [bidder, setBidder] = useState<BidderDetailType | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [selectedDocType, setSelectedDocType] = useState<BidderDocumentType>('pan')
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [selectedDocument, setSelectedDocument] = useState<BidderDocumentDetail | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<number | null>(null)

  const loadBidder = useCallback(async () => {
    if (!id) return null
    try {
      const data = await getBidder(id)
      setBidder(data)
      setError(null)
      return data
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load bidder.'))
      return null
    }
  }, [id])

  useEffect(() => {
    setIsLoading(true)
    loadBidder().finally(() => setIsLoading(false))
  }, [loadBidder])

  // Poll while any document is mid-pipeline.
  useEffect(() => {
    if (!id || !bidder) return
    const anyPolling = bidder.documents.some((d) => POLLING_DOC_STATUSES.has(d.processing_status))

    if (anyPolling) {
      pollRef.current = window.setInterval(async () => {
        const data = await loadBidder()
        if (data && !data.documents.some((d) => POLLING_DOC_STATUSES.has(d.processing_status))) {
          if (pollRef.current) window.clearInterval(pollRef.current)
        }
      }, 2500)
    }

    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, bidder?.documents.map((d) => d.processing_status).join(',')])

  async function handleFileSelected(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !id) return
    setActionError(null)
    setUploadProgress(0)
    try {
      const result = await uploadBidderDocument(id, selectedDocType, file, setUploadProgress)
      // Immediately kick off the extraction pipeline for the newly uploaded document.
      await processBidderDocument(result.document_id)
      await loadBidder()
    } catch (err) {
      setActionError(getErrorMessage(err, 'Upload failed.'))
    } finally {
      setUploadProgress(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleReanalyze() {
    if (!id) return
    setIsAnalyzing(true)
    setActionError(null)
    try {
      await analyzeBidder(id)
      await loadBidder()
    } catch (err) {
      setActionError(getErrorMessage(err, 'Analysis failed.'))
    } finally {
      setIsAnalyzing(false)
    }
  }

  const documentColumns = useMemo<Column<BidderDocumentDetail>[]>(
    () => [
      {
        key: 'document_type',
        header: 'Type',
        render: (d) => (
          <Badge tone="neutral" size="sm">
            {BIDDER_DOCUMENT_TYPE_LABELS[d.document_type]}
          </Badge>
        ),
      },
      {
        key: 'original_filename',
        header: 'Filename',
        render: (d) => (
          <span className="block max-w-[16rem] truncate font-medium text-slate-800">
            {d.original_filename}
          </span>
        ),
      },
      {
        key: 'processing_status',
        header: 'Status',
        render: (d) => <DocumentProcessingStatusBadge status={d.processing_status} />,
      },
      {
        key: 'detected_type',
        header: 'Detected type',
        hideOnMobile: true,
        render: (d) =>
          d.extracted_data?.detected_document_type ? (
            <span
              className={
                d.extracted_data.type_mismatch
                  ? 'inline-flex items-center gap-1 font-medium text-warning-700'
                  : 'text-slate-600'
              }
            >
              {BIDDER_DOCUMENT_TYPE_LABELS[
                d.extracted_data.detected_document_type as BidderDocumentType
              ] ?? d.extracted_data.detected_document_type}
              {d.extracted_data.type_mismatch ? (
                <AlertTriangle className="h-3.5 w-3.5" aria-label="Type mismatch" />
              ) : null}
            </span>
          ) : (
            <span className="text-slate-400">—</span>
          ),
      },
      {
        key: 'confidence',
        header: 'Confidence',
        align: 'right',
        render: (d) => (
          <div className="flex justify-end">
            <ConfidenceIndicator
              confidence={d.extracted_data?.confidence}
              needsReview={d.extracted_data?.needs_review ?? false}
            />
          </div>
        ),
      },
    ],
    [],
  )

  // ---- Loading / error shells -------------------------------------------------
  if (isLoading) {
    return (
      <Layout>
        <PageHeader
          icon={<Building2 className="h-5 w-5" />}
          title="Bidder"
          breadcrumbs={[{ label: 'Bidders', to: '/bidders' }, { label: 'Loading…' }]}
        />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCardSkeleton count={4} />
        </div>
        <div className="mt-16 flex justify-center">
          <Spinner size={28} label="Loading bidder…" />
        </div>
      </Layout>
    )
  }

  if (error || !bidder) {
    return (
      <Layout>
        <PageHeader
          icon={<Building2 className="h-5 w-5" />}
          title="Bidder"
          breadcrumbs={[{ label: 'Bidders', to: '/bidders' }, { label: 'Not found' }]}
        />
        <ErrorState
          title="Unable to load bidder"
          message={error ?? 'This bidder could not be found.'}
          onRetry={() => {
            setIsLoading(true)
            loadBidder().finally(() => setIsLoading(false))
          }}
        />
      </Layout>
    )
  }

  const report = bidder.consistency_report
  const analyzedCount = report?.documents_analyzed ?? 0
  const reviewCount = report?.documents_needing_review ?? 0
  const missingCount = report?.missing_documents.length ?? bidder.missing_document_types?.length ?? 0

  const contactLine = [
    bidder.gem_seller_id ? `GeM: ${bidder.gem_seller_id}` : 'No GeM Seller ID',
    bidder.contact_email || 'No email on file',
    bidder.contact_phone || null,
  ]
    .filter(Boolean)
    .join('  ·  ')

  return (
    <Layout>
      <PageHeader
        icon={<Building2 className="h-5 w-5" />}
        title={bidder.company_name}
        description={contactLine}
        breadcrumbs={[
          { label: 'Bidders', to: `/bidders?tender_id=${bidder.tender_id}` },
          { label: bidder.company_name },
        ]}
        actions={
          <>
            <BidderConsistencyStatusBadge status={bidder.consistency_status} />
            <Button
              variant="outline"
              leftIcon={<FileBarChart className="h-4 w-4" />}
              onClick={() => navigate(`/reports?tender_id=${bidder.tender_id}`)}
            >
              Generate report
            </Button>
          </>
        }
      />

      {actionError && (
        <Alert variant="danger" className="mb-6" onDismiss={() => setActionError(null)}>
          {actionError}
        </Alert>
      )}

      {/* Summary */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Documents"
          value={bidder.documents.length}
          icon={<FileText className="h-5 w-5" />}
          tone="navy"
        />
        <StatCard
          label="Analyzed"
          value={analyzedCount}
          icon={<FileCheck2 className="h-5 w-5" />}
          tone="primary"
        />
        <StatCard
          label="Needs review"
          value={reviewCount}
          icon={<AlertTriangle className="h-5 w-5" />}
          tone={reviewCount > 0 ? 'warning' : 'neutral'}
        />
        <StatCard
          label="Missing docs"
          value={missingCount}
          icon={<FileX2 className="h-5 w-5" />}
          tone={missingCount > 0 ? 'danger' : 'neutral'}
        />
      </div>

      {/* Upload + consistency */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {isManager && (
          <SectionCard
            icon={<UploadCloud className="h-4 w-4" />}
            title="Upload document"
            description="PDF, JPG or PNG. Processing starts automatically."
            className="lg:col-span-1"
          >
            <div className="space-y-4">
              <FormField label="Document type" htmlFor="doc-type">
                <Select
                  id="doc-type"
                  value={selectedDocType}
                  onChange={(e) => setSelectedDocType(e.target.value as BidderDocumentType)}
                >
                  {DOCUMENT_TYPE_OPTIONS.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>
              </FormField>

              <FormField label="File" htmlFor="doc-file">
                <input
                  id="doc-file"
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf,image/jpeg,image/png"
                  onChange={handleFileSelected}
                  disabled={uploadProgress !== null}
                  className="block w-full cursor-pointer rounded-lg border border-slate-300 text-sm text-slate-600 shadow-sm file:mr-3 file:cursor-pointer file:border-0 file:border-r file:border-slate-200 file:bg-slate-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-primary-700 hover:file:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </FormField>

              {uploadProgress !== null && (
                <div>
                  <div className="mb-1 flex justify-between text-xs text-slate-500">
                    <span>Uploading…</span>
                    <span className="tabular-nums">{uploadProgress}%</span>
                  </div>
                  <Progress value={uploadProgress} />
                </div>
              )}
            </div>
          </SectionCard>
        )}

        <SectionCard
          icon={<FileCheck2 className="h-4 w-4" />}
          title="Identity consistency & missing documents"
          description="Cross-document checks across processed uploads."
          className={isManager ? 'lg:col-span-2' : 'lg:col-span-3'}
          actions={
            isManager ? (
              <Button
                variant="outline"
                size="sm"
                onClick={handleReanalyze}
                loading={isAnalyzing}
                leftIcon={<RotateCw className="h-4 w-4" />}
              >
                {isAnalyzing ? 'Analyzing…' : 'Re-run analysis'}
              </Button>
            ) : null
          }
        >
          <BidderConsistencyPanel report={report} />
        </SectionCard>
      </div>

      {/* Documents */}
      <div className="mt-6">
        <SectionCard
          icon={<FileText className="h-4 w-4" />}
          title="Documents"
          description={`${bidder.documents.length} uploaded`}
          flush
        >
          <DataTable
            columns={documentColumns}
            data={bidder.documents}
            rowKey={(d) => d.id}
            onRowClick={(d) => setSelectedDocument(d)}
            empty={
              <EmptyState
                icon={<FileText className="h-6 w-6" />}
                title="No documents uploaded yet"
                description={
                  isManager
                    ? 'Upload a document above to begin AI-assisted extraction.'
                    : 'Documents will appear here once they are uploaded.'
                }
              />
            }
          />
        </SectionCard>
      </div>

      {selectedDocument && (
        <BidderDocumentDetailModal
          document={selectedDocument}
          onClose={() => setSelectedDocument(null)}
        />
      )}

      {/* Compliance verification & rule engine results */}
      <div className="mt-6">
        <ComplianceDashboardPanel bidderId={bidder.id} canManage={isManager} />
      </div>

      {/* Risk Intelligence */}
      <div className="mt-6">
        <SectionCard
          icon={<ShieldAlert className="h-4 w-4" />}
          title="Risk Intelligence"
          description="Deterministic risk score — AI provides narrative only, never the score."
        >
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div>
              <RiskScoreCard score={bidder.risk_score ?? null} level={bidder.risk_level ?? null} />
            </div>
            <div className="lg:col-span-2">
              <WhyRiskyPanel bidderId={bidder.id} canAnalyze={isManager} />
            </div>
          </div>
        </SectionCard>
      </div>

      {/* Evidence Trail */}
      <div className="mt-6">
        <SectionCard
          icon={<Link2 className="h-4 w-4" />}
          title="Evidence Trail"
          description="Full evidence chain from tender clause → requirement → document → verification → verdict."
        >
          <EvidenceTrailPanel bidderId={bidder.id} />
        </SectionCard>
      </div>

      {/* Risk Timeline */}
      <div className="mt-6">
        <SectionCard
          icon={<Clock className="h-4 w-4" />}
          title="Activity Timeline"
          description="Chronological events for this bidder."
        >
          <RiskTimeline bidderId={bidder.id} />
        </SectionCard>
      </div>

      {/* Final Decision */}
      <div className="mt-6">
        <FinalDecisionPanel bidderId={bidder.id} canDecide={isManager} />
      </div>
    </Layout>
  )
}
