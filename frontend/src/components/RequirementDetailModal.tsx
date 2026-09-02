import { FileText, Quote } from 'lucide-react'
import type { TenderRequirement } from '../types'
import { REQUIREMENT_CATEGORY_LABELS } from '../types'
import ConfidenceIndicator from './ConfidenceIndicator'
import Modal from './ui/Modal'
import Badge from './ui/Badge'
import Alert from './ui/Alert'
import { formatCurrency } from '../lib/format'

interface Props {
  requirement: TenderRequirement
  onClose: () => void
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <div className="mt-1 text-sm text-slate-700">{children}</div>
    </div>
  )
}

/** Read-only detail view of a single AI-extracted tender requirement. */
export default function RequirementDetailModal({ requirement, onClose }: Props) {
  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      icon={<FileText className="h-5 w-5" />}
      title={requirement.title}
      description={
        <Badge tone="primary">{REQUIREMENT_CATEGORY_LABELS[requirement.category]}</Badge>
      }
    >
      <div className="space-y-5">
        <Field label="Description">{requirement.description}</Field>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Field label="Mandatory">{requirement.mandatory ? 'Yes' : 'No'}</Field>
          <Field label="Verification type">
            <span className="capitalize">{requirement.verification_type.replace(/_/g, ' ')}</span>
          </Field>
          <Field label="AI confidence">
            <ConfidenceIndicator
              confidence={requirement.confidence}
              needsReview={requirement.needs_review}
            />
          </Field>
          {requirement.minimum_value !== null && requirement.minimum_value !== undefined && (
            <Field label="Minimum value">
              {formatCurrency(requirement.minimum_value, requirement.currency ?? 'INR')}
            </Field>
          )}
          {requirement.period && <Field label="Period">{requirement.period}</Field>}
          {requirement.page_number !== null && requirement.page_number !== undefined && (
            <Field label="Page">Page {requirement.page_number}</Field>
          )}
          {requirement.clause_reference && (
            <Field label="Clause">{requirement.clause_reference}</Field>
          )}
        </div>

        {requirement.required_documents && requirement.required_documents.length > 0 && (
          <Field label="Required documents">
            <ul className="mt-0.5 list-inside list-disc space-y-0.5">
              {requirement.required_documents.map((doc, i) => (
                <li key={i}>{doc}</li>
              ))}
            </ul>
          </Field>
        )}

        {requirement.evidence && (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Evidence (from tender text)
            </p>
            <blockquote className="flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm italic text-slate-600">
              <Quote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" aria-hidden="true" />
              <span>{requirement.evidence}</span>
            </blockquote>
          </div>
        )}

        {requirement.needs_review && (
          <Alert variant="warning" title="Flagged for manual review">
            This requirement was flagged (low AI confidence or ambiguous data). Verify it against
            the source tender document before relying on it.
          </Alert>
        )}
      </div>
    </Modal>
  )
}
