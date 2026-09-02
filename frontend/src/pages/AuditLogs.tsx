import { useEffect, useState, useCallback } from 'react'
import Layout from '../components/Layout'
import { listAuditLogs } from '../api/audit'
import type { AuditLogEntry } from '../types'

const PAGE_SIZE = 20

const ACTION_OPTIONS = [
  { value: '', label: 'All Actions' },
  { value: 'report_generated', label: 'Report Generated' },
  { value: 'password_changed', label: 'Password Changed' },
  { value: 'verification_run', label: 'Verification Run' },
  { value: 'compliance_evaluated', label: 'Compliance Evaluated' },
]

const ENTITY_OPTIONS = [
  { value: '', label: 'All Entities' },
  { value: 'bidder', label: 'Bidder' },
  { value: 'tender', label: 'Tender' },
  { value: 'user', label: 'User' },
]

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [action, setAction] = useState('')
  const [entityType, setEntityType] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)

  const load = useCallback(() => {
    setIsLoading(true)
    setError(null)
    listAuditLogs({
      action: action || undefined,
      entity_type: entityType || undefined,
      page,
      page_size: PAGE_SIZE,
    })
      .then((data) => {
        setLogs(data.items)
        setTotal(data.total)
        setTotalPages(data.total_pages)
      })
      .catch((err) => {
        if (err?.response?.status === 403) {
          setError('You do not have permission to view audit logs.')
        } else {
          setError('Failed to load audit logs')
        }
      })
      .finally(() => setIsLoading(false))
  }, [action, entityType, page])

  useEffect(() => {
    load()
  }, [load])

  return (
    <Layout>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-800">Audit Logs</h2>
        <p className="text-sm text-gray-500">
          A read-only trail of key actions taken across the platform — uploads, verification runs,
          evaluations, and report generation.
        </p>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 px-5 py-4">
          <h3 className="text-sm font-semibold text-gray-700">Activity</h3>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={action}
              onChange={(e) => {
                setAction(e.target.value)
                setPage(1)
              }}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              {ACTION_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <select
              value={entityType}
              onChange={(e) => {
                setEntityType(e.target.value)
                setPage(1)
              }}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              {ENTITY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && <div className="mx-5 mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-gray-500">Timestamp</th>
                <th className="px-4 py-2 text-left font-medium text-gray-500">User</th>
                <th className="px-4 py-2 text-left font-medium text-gray-500">Action</th>
                <th className="px-4 py-2 text-left font-medium text-gray-500">Entity</th>
                <th className="px-4 py-2 text-left font-medium text-gray-500">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-4 py-3" colSpan={5}>
                      <div className="h-4 w-full rounded bg-gray-100" />
                    </td>
                  </tr>
                ))
              ) : logs.length === 0 && !error ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-sm text-gray-500">
                    No audit log entries match the current filters.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-3 text-gray-500">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-gray-700">{log.user_name || '—'}</td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {log.entity_type ? `${log.entity_type} · ${log.entity_id?.slice(0, 8)}...` : '—'}
                    </td>
                    <td className="max-w-md truncate px-4 py-3 text-xs text-gray-400" title={log.details || ''}>
                      {log.details || '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {!isLoading && logs.length > 0 && (
          <div className="flex items-center justify-between border-t border-gray-200 px-5 py-3 text-xs text-gray-500">
            <span>
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="rounded border border-gray-300 px-2.5 py-1 disabled:opacity-40"
              >
                Prev
              </button>
              <span>
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="rounded border border-gray-300 px-2.5 py-1 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
