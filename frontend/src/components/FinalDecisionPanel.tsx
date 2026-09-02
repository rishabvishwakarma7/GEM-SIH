import { useState, useCallback, useEffect } from 'react'
import { Gavel, CheckCircle2, XCircle, MessageSquare, History, AlertTriangle } from 'lucide-react'
import { getFinalDecision, submitFinalDecision, getDecisionHistory } from '../api/risk'
import type { FinalDecision } from '../api/risk'
import { decisionBadge } from '../lib/risk'
import { getErrorMessage } from '../lib/errors'

interface Props {
  bidderId: string
  canDecide: boolean
}

const DECISION_OPTIONS = [
  { value: 'qualified', label: 'Qualified', icon: CheckCircle2, color: 'text-green-600', bg: 'border-green-300 bg-green-50 hover:bg-green-100' },
  { value: 'disqualified', label: 'Disqualified', icon: XCircle, color: 'text-red-600', bg: 'border-red-300 bg-red-50 hover:bg-red-100' },
  { value: 'clarification_required', label: 'Clarification Required', icon: MessageSquare, color: 'text-yellow-600', bg: 'border-yellow-300 bg-yellow-50 hover:bg-yellow-100' },
]

const DECISION_LABELS: Record<string, string> = {
  qualified: 'Qualified',
  disqualified: 'Disqualified',
  clarification_required: 'Clarification Required',
}

export default function FinalDecisionPanel({ bidderId, canDecide }: Props) {
  const [decision, setDecision] = useState<FinalDecision | null>(null)
  const [history, setHistory] = useState<FinalDecision[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [selectedDecision, setSelectedDecision] = useState('')
  const [remarks, setRemarks] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const d = await getFinalDecision(bidderId)
      setDecision(d)
    } catch {
      setDecision(null)
    } finally {
      setLoading(false)
    }
  }, [bidderId])

  useEffect(() => { load() }, [load])

  const handleSubmit = async () => {
    if (!selectedDecision || !remarks.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      const d = await submitFinalDecision(bidderId, selectedDecision, remarks.trim())
      setDecision(d)
      setShowForm(false)
      setSelectedDecision('')
      setRemarks('')
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to submit decision.'))
    } finally {
      setSubmitting(false)
    }
  }

  const loadHistory = async () => {
    try {
      const h = await getDecisionHistory(bidderId)
      setHistory(h)
      setShowHistory(true)
    } catch {
      setHistory([])
    }
  }

  if (loading) return <div className="py-4 text-center text-sm text-slate-400">Loading decision…</div>

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100">
            <Gavel className="h-5 w-5 text-slate-600" />
          </div>
          <div>
            <p className="font-semibold text-slate-800">Final Procurement Decision</p>
            <p className="text-xs text-slate-500">Officer qualification verdict — preserved in audit trail</p>
          </div>
        </div>
        {decision && (
          <button
            onClick={loadHistory}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-primary-600"
          >
            <History className="h-3.5 w-3.5" /> History
          </button>
        )}
      </div>

      <div className="px-5 py-4">
        {/* Existing decision display */}
        {decision && !showForm && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className={`rounded-full px-3 py-1 text-sm font-bold ${decisionBadge(decision.decision)}`}>
                {DECISION_LABELS[decision.decision] ?? decision.decision}
              </span>
              <span className="text-xs text-slate-400">
                v{decision.version} · {new Date(decision.submitted_at).toLocaleString()}
              </span>
            </div>
            <div className="rounded-lg bg-slate-50 p-3">
              <p className="text-xs font-semibold text-slate-500 mb-1">Officer Remarks</p>
              <p className="text-sm text-slate-700">{decision.officer_remarks}</p>
            </div>
            {canDecide && (
              <button
                onClick={() => setShowForm(true)}
                className="text-xs text-primary-600 hover:underline"
              >
                Revise decision (creates new version)
              </button>
            )}
          </div>
        )}

        {/* No decision yet */}
        {!decision && !showForm && (
          <div className="py-2 text-center space-y-3">
            <p className="text-sm text-slate-500">No final decision has been submitted yet.</p>
            {canDecide && (
              <button
                onClick={() => setShowForm(true)}
                className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
              >
                <Gavel className="h-4 w-4" /> Submit Final Decision
              </button>
            )}
          </div>
        )}

        {/* Decision form */}
        {showForm && (
          <div className="space-y-4">
            <p className="text-sm font-semibold text-slate-700">Select Decision</p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {DECISION_OPTIONS.map(opt => {
                const Icon = opt.icon
                return (
                  <button
                    key={opt.value}
                    onClick={() => setSelectedDecision(opt.value)}
                    className={`flex items-center gap-2 rounded-lg border-2 p-3 text-left transition-all ${
                      selectedDecision === opt.value
                        ? opt.bg + ' ring-2 ring-offset-1 ring-primary-300'
                        : 'border-slate-200 bg-white hover:bg-slate-50'
                    }`}
                  >
                    <Icon className={`h-5 w-5 ${opt.color}`} />
                    <span className="text-sm font-medium text-slate-800">{opt.label}</span>
                  </button>
                )
              })}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Officer Remarks <span className="text-red-500">*</span>
              </label>
              <textarea
                value={remarks}
                onChange={e => setRemarks(e.target.value)}
                rows={3}
                placeholder="Provide mandatory remarks explaining the decision…"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400"
              />
              <p className="mt-1 text-xs text-slate-400">
                Remarks are mandatory and will be preserved permanently in the audit trail.
              </p>
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                <AlertTriangle className="h-4 w-4 shrink-0" />{error}
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={handleSubmit}
                disabled={submitting || !selectedDecision || !remarks.trim()}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-60"
              >
                <Gavel className="h-4 w-4" />
                {submitting ? 'Submitting…' : 'Submit Decision'}
              </button>
              <button
                onClick={() => { setShowForm(false); setError(null) }}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* History */}
        {showHistory && history.length > 0 && (
          <div className="mt-4 border-t border-slate-100 pt-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Decision History</p>
            <div className="space-y-2">
              {history.map(h => (
                <div key={h.id} className={`rounded-lg border p-3 text-xs ${h.superseded ? 'opacity-50 bg-slate-50' : 'bg-white'}`}>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 font-semibold ${decisionBadge(h.decision)}`}>
                      {DECISION_LABELS[h.decision]}
                    </span>
                    <span className="text-slate-400">v{h.version}</span>
                    {h.superseded && <span className="text-slate-400">· superseded</span>}
                    <span className="ml-auto text-slate-400">{new Date(h.submitted_at).toLocaleDateString()}</span>
                  </div>
                  <p className="mt-1.5 text-slate-600">{h.officer_remarks}</p>
                </div>
              ))}
            </div>
            <button onClick={() => setShowHistory(false)} className="mt-2 text-xs text-slate-400 hover:text-slate-600">
              Hide history
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
