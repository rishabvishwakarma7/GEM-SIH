import { useState, useCallback, useEffect } from 'react'
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, AlertTriangle, HelpCircle, Link2 } from 'lucide-react'
import { getBidderEvidence } from '../api/risk'
import type { BidderEvidence, RequirementEvidence, EvidenceStep } from '../api/risk'
import { getErrorMessage } from '../lib/errors'

interface Props { bidderId: string }

const STATUS_ICON: Record<string, React.ReactNode> = {
  COMPLIANT:     <CheckCircle2 className="h-4 w-4 text-green-600" />,
  NON_COMPLIANT: <XCircle className="h-4 w-4 text-red-600" />,
  NEEDS_REVIEW:  <AlertTriangle className="h-4 w-4 text-yellow-600" />,
  compliant:     <CheckCircle2 className="h-4 w-4 text-green-600" />,
  non_compliant: <XCircle className="h-4 w-4 text-red-600" />,
  needs_review:  <AlertTriangle className="h-4 w-4 text-yellow-600" />,
  found:         <CheckCircle2 className="h-4 w-4 text-green-600" />,
  missing:       <XCircle className="h-4 w-4 text-red-500" />,
  verified:      <CheckCircle2 className="h-4 w-4 text-green-600" />,
  mismatch:      <XCircle className="h-4 w-4 text-red-600" />,
  not_found:     <AlertTriangle className="h-4 w-4 text-yellow-600" />,
}

const REASON_CODE_LABELS: Record<string, string> = {
  COMPLIANT:                   'Compliant',
  THRESHOLD_NOT_MET:           'Threshold Not Met',
  DOCUMENT_MISSING:            'Document Missing',
  DOCUMENT_UNREADABLE:         'Document Unreadable',
  DOCUMENT_EXPIRED:            'Document Expired',
  FIELD_MISSING:               'Required Field Missing',
  IDENTITY_MISMATCH:           'Identity Mismatch',
  REGISTRY_VERIFICATION_FAILED:'Registry Verification Failed',
  REGISTRY_NOT_FOUND:          'Not Found in Registry',
  LOW_AI_CONFIDENCE:           'Low AI Extraction Confidence',
  MANDATORY_REQUIREMENT_FAILED:'Mandatory Requirement Failed',
  INCONSISTENT_INFORMATION:    'Inconsistent Information',
  SUSPICIOUS_DOCUMENT:         'Suspicious Document',
  DUPLICATE_DOCUMENT:          'Duplicate Document',
  MANUAL_REVIEW_REQUIRED:      'Manual Review Required',
}

function statusBadge(status: string) {
  const base = 'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold'
  if (status === 'COMPLIANT' || status === 'compliant')
    return `${base} bg-green-100 text-green-800`
  if (status === 'NON_COMPLIANT' || status === 'non_compliant')
    return `${base} bg-red-100 text-red-800`
  return `${base} bg-yellow-100 text-yellow-800`
}

function StepIcon({ status }: { status: string | null }) {
  if (!status) return <div className="h-5 w-5 rounded-full bg-slate-200" />
  return (STATUS_ICON[status] as React.ReactElement) ?? <HelpCircle className="h-4 w-4 text-slate-400" />
}

function EvidenceChain({ steps }: { steps: EvidenceStep[] }) {
  return (
    <div className="mt-3 space-y-0">
      {steps.map((step, i) => (
        <div key={i} className="relative flex items-start gap-3 pb-3 pl-7">
          {/* Vertical connector */}
          {i < steps.length - 1 && (
            <div className="absolute left-[9px] top-5 h-full w-0.5 bg-slate-100" />
          )}
          <div className="absolute left-0 top-1">
            <StepIcon status={step.status} />
          </div>
          <div className="min-w-0 flex-1 rounded-md border border-slate-100 bg-slate-50 px-3 py-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{step.label}</span>
              {step.value && (
                <span className="text-xs font-medium text-slate-800">{step.value}</span>
              )}
            </div>
            {step.detail && (
              <p className="mt-0.5 text-xs text-slate-500 italic">&ldquo;{step.detail.slice(0, 200)}{step.detail.length > 200 ? '…' : ''}&rdquo;</p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function RequirementRow({ req }: { req: RequirementEvidence }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <button
        onClick={() => setExpanded(e => !e)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-slate-50"
      >
        {STATUS_ICON[req.status] ?? <HelpCircle className="h-4 w-4 text-slate-400" />}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-slate-800">{req.requirement_title}</p>
            {req.mandatory && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">Mandatory</span>
            )}
            <span className={statusBadge(req.status)}>
              {req.status.replace('_', ' ')}
            </span>
            {req.reason_code && req.reason_code !== 'COMPLIANT' && (
              <span className="rounded-full bg-orange-50 px-2 py-0.5 text-xs text-orange-700 border border-orange-100">
                {REASON_CODE_LABELS[req.reason_code] ?? req.reason_code}
              </span>
            )}
          </div>
          <div className="mt-0.5 flex flex-wrap gap-3 text-xs text-slate-500">
            {req.required_value && <span>Required: <strong>{req.required_value}</strong></span>}
            {req.actual_value && <span>Found: <strong>{req.actual_value}</strong></span>}
          </div>
        </div>
        {expanded
          ? <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
          : <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />}
      </button>

      {expanded && (
        <div className="border-t border-slate-100 px-4 pb-4 pt-3">
          {/* Evidence snippet */}
          {req.evidence?.snippet ? (
            <div className="mb-3 rounded-md border border-blue-100 bg-blue-50 p-3">
              <p className="text-xs font-semibold text-blue-700 mb-1">Evidence Snippet</p>
              <p className="text-xs text-blue-900 italic">&ldquo;{req.evidence.snippet}&rdquo;</p>
              {req.evidence.document_name && (
                <p className="mt-1 text-xs text-blue-600">
                  Source: {req.evidence.document_name}
                  {req.evidence.page_number ? ` — Page ${req.evidence.page_number}` : ''}
                </p>
              )}
            </div>
          ) : (
            <div className="mb-3 rounded-md border border-slate-100 bg-slate-50 p-3 text-xs text-slate-400">
              Evidence unavailable — manual review required.
            </div>
          )}

          {/* Verification */}
          {req.verification && (
            <div className="mb-3 flex items-center gap-3 text-xs">
              <span className="text-slate-500">Government Verification:</span>
              <span className="font-medium text-slate-700">{req.verification.provider ?? '—'}</span>
              {req.verification.status && (
                <span className={`rounded-full px-2 py-0.5 font-semibold ${
                  req.verification.status === 'verified' ? 'bg-green-100 text-green-700'
                  : req.verification.status === 'mismatch' ? 'bg-red-100 text-red-700'
                  : 'bg-yellow-100 text-yellow-700'
                }`}>
                  {req.verification.status.toUpperCase()}
                </span>
              )}
            </div>
          )}

          {/* Evidence chain */}
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500 flex items-center gap-1">
            <Link2 className="h-3 w-3" /> Evidence Trail
          </p>
          {req.evidence_chain.length > 0
            ? <EvidenceChain steps={req.evidence_chain} />
            : <p className="text-xs text-slate-400">No evidence chain available.</p>
          }
        </div>
      )}
    </div>
  )
}

export default function EvidenceTrailPanel({ bidderId }: Props) {
  const [data, setData] = useState<BidderEvidence | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'failed' | 'review' | 'passed'>('all')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await getBidderEvidence(bidderId))
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load evidence.'))
    } finally {
      setLoading(false)
    }
  }, [bidderId])

  useEffect(() => { load() }, [load])

  if (loading) return <div className="py-6 text-center text-sm text-slate-400">Loading evidence trail…</div>
  if (error) return <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
  if (!data) return null

  const filtered = data.requirement_results.filter(r => {
    if (filter === 'failed')  return r.status === 'NON_COMPLIANT'
    if (filter === 'review')  return r.status === 'NEEDS_REVIEW'
    if (filter === 'passed')  return r.status === 'COMPLIANT'
    return true
  })

  const counts = {
    passed: data.requirement_results.filter(r => r.status === 'COMPLIANT').length,
    failed: data.requirement_results.filter(r => r.status === 'NON_COMPLIANT').length,
    review: data.requirement_results.filter(r => r.status === 'NEEDS_REVIEW').length,
  }

  return (
    <div className="space-y-4">
      {/* Filter tabs */}
      <div className="flex flex-wrap gap-2">
        {([['all', 'All', data.requirement_results.length],
           ['passed', 'Compliant', counts.passed],
           ['failed', 'Failed', counts.failed],
           ['review', 'Needs Review', counts.review],
        ] as [string, string, number][]).map(([val, label, count]) => (
          <button
            key={val}
            onClick={() => setFilter(val as typeof filter)}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              filter === val
                ? 'bg-primary-600 text-white border-primary-600'
                : 'bg-white text-slate-600 border-slate-200 hover:border-primary-300'
            }`}
          >
            {label} <span className="ml-1 opacity-70">({count})</span>
          </button>
        ))}
      </div>

      {/* Requirement rows */}
      <div className="space-y-2">
        {filtered.length === 0
          ? <p className="text-center text-sm text-slate-400 py-4">No requirements match this filter.</p>
          : filtered.map(req => <RequirementRow key={req.requirement_id} req={req} />)
        }
      </div>
    </div>
  )
}
