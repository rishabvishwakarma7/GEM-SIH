import axios from 'axios'

/**
 * Extract a safe, human-readable message from an unknown error (typically an
 * Axios error). Never surfaces stack traces or raw 500 bodies to the user.
 */
export function getErrorMessage(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status
    const detail = err.response?.data?.detail

    if (status === 401) return 'Your session has expired. Please sign in again.'
    if (status === 403) return "You don't have permission to perform this action."
    if (status === 404) return 'The requested item could not be found.'

    if (typeof detail === 'string' && detail.trim()) return detail
    // FastAPI validation errors arrive as an array of {msg, loc}.
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0]
      if (first && typeof first.msg === 'string') return first.msg
    }
    if (status && status >= 500) {
      return 'The server encountered an error. Please try again shortly.'
    }
    if (err.code === 'ERR_NETWORK') {
      return 'Unable to reach the server. Check your connection and try again.'
    }
  }
  return fallback
}
