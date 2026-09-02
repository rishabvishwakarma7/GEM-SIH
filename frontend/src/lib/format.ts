/**
 * Small, dependency-free formatting helpers shared across pages so dates,
 * scores and identifiers render consistently. All guard against null / invalid
 * input and fall back to an em-dash rather than throwing or showing "Invalid Date".
 */

const EMPTY = '—' // em-dash

function toDate(input?: string | null): Date | null {
  if (!input) return null
  const d = new Date(input)
  return Number.isNaN(d.getTime()) ? null : d
}

/** e.g. "05 Aug 2026" */
export function formatDate(input?: string | null): string {
  const d = toDate(input)
  if (!d) return EMPTY
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

/** e.g. "05 Aug 2026, 02:30 PM" */
export function formatDateTime(input?: string | null): string {
  const d = toDate(input)
  if (!d) return EMPTY
  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** e.g. "just now", "5 min ago", "3 hours ago", "2 days ago", else a date. */
export function formatRelativeTime(input?: string | null): string {
  const d = toDate(input)
  if (!d) return EMPTY
  const diffMs = Date.now() - d.getTime()
  const sec = Math.round(diffMs / 1000)
  if (sec < 0) return formatDate(input)
  if (sec < 45) return 'just now'
  const min = Math.round(sec / 60)
  if (min < 60) return `${min} min ago`
  const hr = Math.round(min / 60)
  if (hr < 24) return `${hr} hour${hr === 1 ? '' : 's'} ago`
  const day = Math.round(hr / 24)
  if (day < 7) return `${day} day${day === 1 ? '' : 's'} ago`
  return formatDate(input)
}

/** Round a 0–100 compliance score to a whole percentage, or em-dash. */
export function formatScore(score?: number | null): string {
  if (score === null || score === undefined) return EMPTY
  return `${Math.round(score)}%`
}

/** Format a 0–1 confidence as a whole percentage, or em-dash. */
export function formatConfidence(confidence?: number | null): string {
  if (confidence === null || confidence === undefined) return EMPTY
  return `${Math.round(confidence * 100)}%`
}

/** Compact currency in INR (e.g. "₹1.5 Cr", "₹40.0 L", "₹5,000"). */
export function formatCurrency(value?: number | null, currency = 'INR'): string {
  if (value === null || value === undefined) return EMPTY
  const symbol = currency === 'INR' ? '₹' : `${currency} `
  if (value >= 1_00_00_000) return `${symbol}${(value / 1_00_00_000).toFixed(2)} Cr`
  if (value >= 1_00_000) return `${symbol}${(value / 1_00_000).toFixed(2)} L`
  return `${symbol}${value.toLocaleString('en-IN')}`
}
