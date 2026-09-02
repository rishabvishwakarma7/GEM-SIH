import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ClipboardList, ArrowUpRight, ChevronUp } from 'lucide-react'
import Layout from '../components/Layout'
import { listReviewCases, escalateReviewCase } from '../api/reviews'
import type { ReviewCase, ReviewListResponse } from '../api/reviews'
import { reviewStatusBadge, riskBadgeClass } from '../lib/risk'
import { getErrorMessage } from '../lib/errors'
import { formatRelativeTime } from '../lib/format'

const STATUS_FILTERS = [
  { value: '', label: 'All statuses' },
  { value: 'open', label: 'Open' },
  { value: 'assigned', label: 'Assigned' },
  { value: 'in_review', label: 'In Review' },
  { value: 'escalated', label: 'Escalated' },
  { value: 'clarification_required', label: 'Clarification Required' },
  { value: 'closed', label: 'Closed' },
]

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'text-red-700 font-bold',
  high: 'text-orange-600 font-semibold',
  medium: 'text-yellow-600',
  low: 'text-slate-500',
}

const LEVEL_LABELS: Record<string, string> = {
  evaluator: 'Evaluator',
  senior_evaluator: 'Senior Evaluator',
  procurement_officer: 'Procurement Officer',
}

export default function ReviewQueue() {
  const navigate = useNavigate()
  const [data, setData] = useState<ReviewListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 20

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listReviewCases({
        status: statusFilter || undefined,
        page,
        page_size: PAGE_SIZE,
      })
      setData(res)
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load review queue.'))
    } finally {
      setLoading(false)
    }
  }, [statusFilter, page])

  useEffect(() => { load() }, [load])

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-100">
            <ClipboardList className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Review Queue</h1>
            <p className="text-sm text-slate-500">
              Multi-level human review workflow for compliance cases
            </p>
          </div>
          {data && (
            <span className="ml-auto rounded-full bg-purple-100 px-3 py-1 text-sm font-bold text-purple-700">
              {data.total} cases
            </span>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 rounded-lg border border-slate-200 bg-white p-3">
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
          >
            {STATUS_FILTERS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
        </div>

        {error && <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>}

        {loading ? (
          <div className="py-8 text-center text-sm text-slate-400">Loading review cases…</div>
        ) : !data || data.items.length === 0 ? (
          <div className="py-12 text-center">
            <ClipboardList className="mx-auto mb-3 h-10 w-10 text-slate-200" />
            <p className="text-slate-500">No review cases match your filters.</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 text-left">Priority</th>
                  <th className="px-4 py-3 text-left">Bidder / Tender</th>
                  <th className="px-4 py-3 text-left">Review Level</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Created</th>
                  <th className="px-4 py-3 text-left">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map(c => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <span className={`text-xs ${PRIORITY_COLORS[c.priority] ?? ''}`}>
                        {c.priority.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-800 text-xs truncate max-w-[14rem]">
                        {c.bidder_id}
                      </p>
                      {c.reason && (
                        <p className="text-xs text-slate-400 truncate max-w-[14rem]">{c.reason}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      {LEVEL_LABELS[c.review_level] ?? c.review_level}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${reviewStatusBadge(c.status)}`}>
                        {c.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {formatRelativeTime(c.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => navigate(`/bidders/${c.bidder_id}`)}
                        className="inline-flex items-center gap-1 rounded bg-primary-50 px-2.5 py-1 text-xs font-medium text-primary-700 hover:bg-primary-100"
                      >
                        <ArrowUpRight className="h-3 w-3" /> Review
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="flex items-center justify-between text-sm text-slate-500">
            <span>{data.total} total cases</span>
            <div className="flex gap-2">
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                className="rounded border border-slate-200 px-3 py-1 disabled:opacity-40 hover:bg-slate-50">Prev</button>
              <span className="px-2 py-1">Page {page} / {data.total_pages}</span>
              <button disabled={page >= data.total_pages} onClick={() => setPage(p => p + 1)}
                className="rounded border border-slate-200 px-3 py-1 disabled:opacity-40 hover:bg-slate-50">Next</button>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
