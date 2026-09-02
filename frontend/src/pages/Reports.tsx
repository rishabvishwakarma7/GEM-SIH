import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { FileBarChart, FileText, FileSpreadsheet, Download, Building2, History } from 'lucide-react'
import Layout from '../components/Layout'
import {
  PageHeader,
  SectionCard,
  FormField,
  Select,
  DataTable,
  Button,
  Badge,
  Alert,
  EmptyState,
  Skeleton,
} from '../components/ui'
import type { Column } from '../components/ui'
import { listTenders } from '../api/tenders'
import { listBidders } from '../api/bidders'
import {
  downloadBidderReportPdf,
  downloadBidderReportCsv,
  listTenderReports,
  downloadReportById,
} from '../api/reports'
import type { Tender, Bidder, ReportRecord } from '../types'
import { formatDateTime } from '../lib/format'

export default function Reports() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTenderId = searchParams.get('tender_id') || ''

  const [tenders, setTenders] = useState<Tender[]>([])
  const [tendersLoading, setTendersLoading] = useState(true)
  const [selectedTenderId, setSelectedTenderId] = useState(initialTenderId)

  const [bidders, setBidders] = useState<Bidder[]>([])
  const [biddersLoading, setBiddersLoading] = useState(false)
  const [biddersError, setBiddersError] = useState<string | null>(null)

  const [pastReports, setPastReports] = useState<ReportRecord[]>([])
  const [pastReportsLoading, setPastReportsLoading] = useState(false)

  const [generatingId, setGeneratingId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    listTenders()
      .then(setTenders)
      .catch(() => setActionError('Failed to load tenders'))
      .finally(() => setTendersLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedTenderId) {
      setBidders([])
      setPastReports([])
      return
    }
    setSearchParams({ tender_id: selectedTenderId })

    setBiddersLoading(true)
    setBiddersError(null)
    listBidders(selectedTenderId)
      .then(setBidders)
      .catch(() => setBiddersError('Failed to load bidders for this tender'))
      .finally(() => setBiddersLoading(false))

    setPastReportsLoading(true)
    listTenderReports(selectedTenderId)
      .then(setPastReports)
      .catch(() => {})
      .finally(() => setPastReportsLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTenderId])

  async function handleDownload(bidder: Bidder, format: 'pdf' | 'csv') {
    setActionError(null)
    setGeneratingId(`${bidder.id}-${format}`)
    try {
      if (format === 'pdf') {
        await downloadBidderReportPdf(bidder.id, bidder.company_name)
      } else {
        await downloadBidderReportCsv(bidder.id, bidder.company_name)
      }
      // refresh past-reports list since a new one was just persisted server-side
      if (selectedTenderId) {
        listTenderReports(selectedTenderId).then(setPastReports).catch(() => {})
      }
    } catch (err: any) {
      setActionError(
        err?.response?.data?.detail ||
          'Report generation failed — make sure verification has been run for this bidder first.',
      )
    } finally {
      setGeneratingId(null)
    }
  }

  const columns: Column<Bidder>[] = [
    {
      key: 'company_name',
      header: 'Bidder',
      render: (b) => <span className="font-medium text-slate-800">{b.company_name}</span>,
    },
    {
      key: 'gem_seller_id',
      header: 'GeM Seller ID',
      hideOnMobile: true,
      render: (b) =>
        b.gem_seller_id ? (
          <span className="font-mono text-xs text-slate-600">{b.gem_seller_id}</span>
        ) : (
          <span className="text-slate-400">—</span>
        ),
    },
    {
      key: 'report',
      header: 'Report',
      align: 'right',
      render: (b) => (
        <div className="flex justify-end gap-2">
          <Button
            size="sm"
            leftIcon={<FileText className="h-4 w-4" />}
            loading={generatingId === `${b.id}-pdf`}
            disabled={generatingId === `${b.id}-pdf`}
            onClick={() => handleDownload(b, 'pdf')}
          >
            PDF
          </Button>
          <Button
            size="sm"
            variant="outline"
            leftIcon={<FileSpreadsheet className="h-4 w-4" />}
            loading={generatingId === `${b.id}-csv`}
            disabled={generatingId === `${b.id}-csv`}
            onClick={() => handleDownload(b, 'csv')}
          >
            CSV
          </Button>
        </div>
      ),
    },
  ]

  return (
    <Layout>
      <PageHeader
        icon={<FileBarChart className="h-5 w-5" />}
        title="Reports"
        description="Generate and download PDF or CSV compliance reports for any bidder that has completed verification."
        breadcrumbs={[{ label: 'Reports' }]}
      />

      <div className="space-y-6">
        <SectionCard icon={<FileText className="h-4 w-4" />} title="Select tender">
          {tendersLoading ? (
            <Skeleton className="h-10 w-full max-w-md" />
          ) : (
            <FormField label="Tender" htmlFor="tender-select" className="max-w-md">
              <Select
                id="tender-select"
                value={selectedTenderId}
                onChange={(e) => setSelectedTenderId(e.target.value)}
              >
                <option value="">— Choose a tender —</option>
                {tenders.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.tender_ref_no} — {t.title}
                  </option>
                ))}
              </Select>
            </FormField>
          )}
        </SectionCard>

        {actionError && (
          <Alert variant="danger" onDismiss={() => setActionError(null)}>
            {actionError}
          </Alert>
        )}

        {selectedTenderId && (
          <>
            <SectionCard
              icon={<Building2 className="h-4 w-4" />}
              title="Bidders in this tender"
              description="Generate a fresh report or download an existing one."
              flush
            >
              {biddersError ? (
                <div className="p-5">
                  <Alert variant="danger">{biddersError}</Alert>
                </div>
              ) : (
                <DataTable
                  columns={columns}
                  data={bidders}
                  rowKey={(b) => b.id}
                  loading={biddersLoading}
                  skeletonRows={4}
                  empty={
                    <EmptyState
                      icon={<Building2 className="h-6 w-6" />}
                      title="No bidders yet"
                      description="No bidders have been added to this tender yet."
                    />
                  }
                />
              )}
            </SectionCard>

            <SectionCard icon={<History className="h-4 w-4" />} title="Previously generated reports" flush>
              {pastReportsLoading ? (
                <div className="space-y-2 p-5">
                  <Skeleton className="h-5 w-full" />
                  <Skeleton className="h-5 w-2/3" />
                </div>
              ) : pastReports.length === 0 ? (
                <EmptyState
                  compact
                  icon={<History className="h-6 w-6" />}
                  title="No reports yet"
                  description="No reports have been generated for this tender yet."
                />
              ) : (
                <ul className="divide-y divide-slate-100">
                  {pastReports.map((r) => (
                    <li key={r.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                      <div className="flex min-w-0 items-center gap-3">
                        <Badge tone="neutral" size="sm">
                          {r.report_type}
                        </Badge>
                        <span className="text-xs text-slate-400">
                          {formatDateTime(r.generated_at)}
                        </span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        leftIcon={<Download className="h-4 w-4" />}
                        onClick={() =>
                          downloadReportById(r.id, r.file_path.split('/').pop() || 'report')
                        }
                      >
                        Re-download
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </SectionCard>
          </>
        )}
      </div>
    </Layout>
  )
}
