import { FileCheck2, FileX2, AlertTriangle } from 'lucide-react'
import type { BidderConsistencyReport } from '../types'
import { BIDDER_DOCUMENT_TYPE_LABELS } from '../types'
import Alert from './ui/Alert'
import EmptyState from './ui/EmptyState'
import { cn } from '../lib/cn'

interface Props {
  report: BidderConsistencyReport | null | undefined
}

interface Tile {
  label: string
  value: number
  icon: JSX.Element
  wrap: string
  text: string
}

/** Cross-document consistency summary for a bidder (missing docs + identity checks). */
export default function BidderConsistencyPanel({ report }: Props) {
  if (!report) {
    return (
      <EmptyState
        compact
        icon={<FileCheck2 className="h-6 w-6" />}
        title="No analysis yet"
        description='Upload and process at least one document, or click "Re-run analysis".'
      />
    )
  }

  const hasIssues = report.missing_documents.length > 0 || report.identity_warnings.length > 0

  const tiles: Tile[] = [
    {
      label: 'Analyzed',
      value: report.documents_analyzed,
      icon: <FileCheck2 className="h-4 w-4" />,
      wrap: 'bg-primary-50 border-primary-100',
      text: 'text-primary-700',
    },
    {
      label: 'Failed / Unreadable',
      value: report.documents_failed,
      icon: <FileX2 className="h-4 w-4" />,
      wrap: 'bg-danger-50 border-danger-100',
      text: 'text-danger-700',
    },
    {
      label: 'Needs Review',
      value: report.documents_needing_review,
      icon: <AlertTriangle className="h-4 w-4" />,
      wrap: 'bg-warning-50 border-warning-100',
      text: 'text-warning-700',
    },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        {tiles.map((t) => (
          <div
            key={t.label}
            className={cn('rounded-card border p-3 text-center', t.wrap)}
          >
            <div className={cn('mb-1 flex items-center justify-center gap-1.5', t.text)}>
              {t.icon}
              <span className="text-2xl font-bold tabular-nums">{t.value}</span>
            </div>
            <p className="text-xs text-slate-500">{t.label}</p>
          </div>
        ))}
      </div>

      {report.missing_documents.length > 0 && (
        <Alert variant="warning" title="Missing mandatory documents">
          <ul className="mt-1 list-inside list-disc space-y-0.5">
            {report.missing_documents.map((docType) => (
              <li key={docType}>
                {BIDDER_DOCUMENT_TYPE_LABELS[docType as keyof typeof BIDDER_DOCUMENT_TYPE_LABELS] ??
                  docType}
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {report.identity_warnings.length > 0 && (
        <Alert variant="danger" title="Identity inconsistencies detected">
          <ul className="mt-1 space-y-1.5">
            {report.identity_warnings.map((w, i) => (
              <li key={i}>
                <span className="font-semibold capitalize">{w.field.replace(/_/g, ' ')}:</span>{' '}
                {w.message}
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {!hasIssues && (
        <Alert variant="success" title="No inconsistencies found">
          No missing mandatory documents or identity inconsistencies were detected across the
          processed documents.
        </Alert>
      )}
    </div>
  )
}
