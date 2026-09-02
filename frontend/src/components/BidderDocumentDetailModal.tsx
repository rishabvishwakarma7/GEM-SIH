import { FileText, Quote } from 'lucide-react'
import type { BidderDocumentDetail } from '../types'
import { BIDDER_DOCUMENT_TYPE_LABELS } from '../types'
import ConfidenceIndicator from './ConfidenceIndicator'
import Modal from './ui/Modal'
import Badge from './ui/Badge'
import Alert from './ui/Alert'
import { formatConfidence } from '../lib/format'

interface Props {
  document: BidderDocumentDetail
  onClose: () => void
}

function docLabel(type: string): string {
  return BIDDER_DOCUMENT_TYPE_LABELS[type as keyof typeof BIDDER_DOCUMENT_TYPE_LABELS] ?? type
}

/** Read-only detail view of an AI-classified bidder document + extracted fields. */
export default function BidderDocumentDetailModal({ document, onClose }: Props) {
  const data = document.extracted_data

  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      icon={<FileText className="h-5 w-5" />}
      title={document.original_filename}
      description={<Badge tone="primary">{docLabel(document.document_type)}</Badge>}
    >
      <div className="space-y-4">
        {!data ? (
          <p className="text-sm text-slate-500">No extraction data available yet.</p>
        ) : (
          <>
            {!data.is_readable && (
              <Alert variant="danger" title="Document could not be read reliably">
                Poor scan quality, blank, or unrecognizable content. Ask the bidder to re-upload a
                clearer copy.
              </Alert>
            )}

            {data.type_mismatch && (
              <Alert variant="warning" title="Document type mismatch">
                AI detected this as a{' '}
                <strong>
                  {data.detected_document_type ? docLabel(data.detected_document_type) : 'different'}
                </strong>{' '}
                document, which differs from the declared type ({docLabel(document.document_type)}).
                Please verify.
              </Alert>
            )}

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Extraction confidence
                </p>
                <div className="mt-1">
                  <ConfidenceIndicator confidence={data.confidence} needsReview={data.needs_review} />
                </div>
              </div>
              {data.classification_confidence !== null &&
                data.classification_confidence !== undefined && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Classification confidence
                    </p>
                    <p className="mt-1 text-sm tabular-nums text-slate-700">
                      {formatConfidence(data.classification_confidence)}
                    </p>
                  </div>
                )}
              {data.page_number !== null && data.page_number !== undefined && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Page</p>
                  <p className="mt-1 text-sm text-slate-700">Page {data.page_number}</p>
                </div>
              )}
            </div>

            {data.structured_fields && Object.keys(data.structured_fields).length > 0 && (
              <div>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Extracted fields
                </p>
                <div className="overflow-hidden rounded-lg border border-slate-200">
                  <table className="w-full text-sm">
                    <tbody className="divide-y divide-slate-100">
                      {Object.entries(data.structured_fields).map(([key, value]) => (
                        <tr key={key}>
                          <td className="w-1/3 bg-slate-50 px-3 py-2 font-medium capitalize text-slate-600">
                            {key.replace(/_/g, ' ')}
                          </td>
                          <td className="px-3 py-2 text-slate-800">
                            {value === null || value === undefined || value === '' ? (
                              <span className="italic text-slate-400">Not found</span>
                            ) : (
                              String(value)
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {data.missing_fields && data.missing_fields.length > 0 && (
              <Alert variant="warning" title="Missing / unreadable fields">
                <ul className="mt-1 list-inside list-disc">
                  {data.missing_fields.map((f) => (
                    <li key={f} className="capitalize">
                      {f.replace(/_/g, ' ')}
                    </li>
                  ))}
                </ul>
              </Alert>
            )}

            {data.evidence && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Evidence (from document text)
                </p>
                <blockquote className="flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm italic text-slate-600">
                  <Quote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" aria-hidden="true" />
                  <span>{data.evidence}</span>
                </blockquote>
              </div>
            )}

            {data.needs_review && (
              <Alert variant="warning" title="Flagged for manual review">
                Low confidence, missing fields, a type mismatch, or unreadable content. Verify
                against the original file.
              </Alert>
            )}
          </>
        )}

        {document.processing_error && (
          <Alert variant="danger" title="Processing error">
            {document.processing_error}
          </Alert>
        )}
      </div>
    </Modal>
  )
}
