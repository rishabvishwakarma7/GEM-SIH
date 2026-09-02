import { useEffect, useState, useCallback } from 'react'
import { Bell, CheckCheck, EyeOff, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'
import { listAlerts, markAlertRead, dismissAlert } from '../api/alerts'
import type { Alert, AlertListResponse } from '../api/alerts'
import { severityBadgeClass } from '../lib/risk'
import { getErrorMessage } from '../lib/errors'
import { formatRelativeTime } from '../lib/format'

const SEVERITY_FILTERS = [
  { value: '', label: 'All severities' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
  { value: 'info', label: 'Info' },
]

const EVENT_TYPE_FILTERS = [
  { value: '', label: 'All types' },
  { value: 'mandatory_requirement_failed', label: 'Mandatory Failed' },
  { value: 'compliance_non_compliant', label: 'Non-Compliant' },
  { value: 'high_risk_bidder', label: 'High Risk' },
  { value: 'suspicious_document', label: 'Suspicious Document' },
  { value: 'duplicate_document', label: 'Duplicate Document' },
  { value: 'registry_mismatch', label: 'Registry Mismatch' },
  { value: 'identity_inconsistency', label: 'Identity Issue' },
  { value: 'human_review_required', label: 'Review Required' },
  { value: 'review_escalated', label: 'Escalated' },
  { value: 'final_decision_submitted', label: 'Final Decision' },
]

function AlertRow({ alert, onRead, onDismiss }: {
  alert: Alert
  onRead: (id: string) => void
  onDismiss: (id: string) => void
}) {
  const navigate = useNavigate()
  const isUnread = !alert.read_at

  const handleOpen = () => {
    onRead(alert.id)
    if (alert.bidder_id) navigate(`/bidders/${alert.bidder_id}`)
  }

  return (
    <div className={`rounded-lg border px-4 py-3 transition-colors ${
      isUnread ? 'border-primary-200 bg-primary-50' : 'border-slate-200 bg-white'
    }`}>
      <div className="flex items-start gap-3">
        {/* Unread dot */}
        <div className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${isUnread ? 'bg-primary-500' : 'bg-transparent'}`} />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${severityBadgeClass(alert.severity)}`}>
              {alert.severity.toUpperCase()}
            </span>
            <p className="text-sm font-semibold text-slate-800">{alert.title}</p>
            {alert.action_required && (
              <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                Action Required
              </span>
            )}
            <span className="ml-auto text-xs text-slate-400">{formatRelativeTime(alert.created_at)}</span>
          </div>

          {alert.description && (
            <p className="mt-1 text-xs text-slate-600">{alert.description}</p>
          )}

          <div className="mt-2 flex items-center gap-2">
            {alert.bidder_id && (
              <button
                onClick={handleOpen}
                className="inline-flex items-center gap-1 text-xs text-primary-600 hover:underline"
              >
                <ExternalLink className="h-3 w-3" /> Open Bidder
              </button>
            )}
            {isUnread && (
              <button
                onClick={() => onRead(alert.id)}
                className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700"
              >
                <CheckCheck className="h-3 w-3" /> Mark Read
              </button>
            )}
            <button
              onClick={() => onDismiss(alert.id)}
              className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600"
            >
              <EyeOff className="h-3 w-3" /> Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AlertsPage() {
  const [data, setData] = useState<AlertListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [severity, setSeverity] = useState('')
  const [eventType, setEventType] = useState('')
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 25

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listAlerts({
        severity: severity || undefined,
        event_type: eventType || undefined,
        unread_only: unreadOnly,
        page,
        page_size: PAGE_SIZE,
      })
      setData(res)
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load alerts.'))
    } finally {
      setLoading(false)
    }
  }, [severity, eventType, unreadOnly, page])

  useEffect(() => { load() }, [load])

  const handleRead = async (id: string) => {
    await markAlertRead(id)
    load()
  }

  const handleDismiss = async (id: string) => {
    await dismissAlert(id)
    load()
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-100">
              <Bell className="h-5 w-5 text-orange-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800">Alert Center</h1>
              <p className="text-sm text-slate-500">
                Event-driven alerts from compliance, risk, and document analysis pipelines
              </p>
            </div>
          </div>
          {data && (
            <span className="rounded-full bg-red-100 px-3 py-1 text-sm font-bold text-red-700">
              {data.unread_count} unread
            </span>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 rounded-lg border border-slate-200 bg-white p-3">
          <select
            value={severity}
            onChange={e => { setSeverity(e.target.value); setPage(1) }}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
          >
            {SEVERITY_FILTERS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
          <select
            value={eventType}
            onChange={e => { setEventType(e.target.value); setPage(1) }}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
          >
            {EVENT_TYPE_FILTERS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={e => { setUnreadOnly(e.target.checked); setPage(1) }}
              className="rounded border-slate-300"
            />
            Unread only
          </label>
        </div>

        {/* Alerts list */}
        {error && <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>}

        {loading ? (
          <div className="py-8 text-center text-sm text-slate-400">Loading alerts…</div>
        ) : data && data.items.length === 0 ? (
          <div className="py-12 text-center">
            <Bell className="mx-auto mb-3 h-10 w-10 text-slate-200" />
            <p className="text-slate-500">No alerts match your filters.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {data?.items.map(a => (
              <AlertRow key={a.id} alert={a} onRead={handleRead} onDismiss={handleDismiss} />
            ))}
          </div>
        )}

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="flex items-center justify-between text-sm text-slate-500">
            <span>{data.total} total alerts</span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
                className="rounded border border-slate-200 px-3 py-1 disabled:opacity-40 hover:bg-slate-50"
              >Prev</button>
              <span className="px-2 py-1">Page {page} / {data.total_pages}</span>
              <button
                disabled={page >= data.total_pages}
                onClick={() => setPage(p => p + 1)}
                className="rounded border border-slate-200 px-3 py-1 disabled:opacity-40 hover:bg-slate-50"
              >Next</button>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
