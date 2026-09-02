import apiClient from './client'

export interface Alert {
  id: string
  event_type: string
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical'
  title: string
  description: string | null
  tender_id: string | null
  bidder_id: string | null
  requirement_id: string | null
  document_id: string | null
  action_required: boolean
  read_at: string | null
  dismissed: boolean
  created_at: string
}

export interface AlertListResponse {
  items: Alert[]
  total: number
  unread_count: number
  page: number
  page_size: number
  total_pages: number
}

export interface UnreadAlertsResponse {
  unread_count: number
  alerts: Alert[]
}

export async function listAlerts(params: {
  severity?: string
  event_type?: string
  bidder_id?: string
  tender_id?: string
  unread_only?: boolean
  action_required?: boolean
  page?: number
  page_size?: number
}): Promise<AlertListResponse> {
  const res = await apiClient.get<AlertListResponse>('/alerts/', { params })
  return res.data
}

export async function getUnreadAlerts(limit = 10): Promise<UnreadAlertsResponse> {
  const res = await apiClient.get<UnreadAlertsResponse>('/alerts/unread', { params: { limit } })
  return res.data
}

export async function markAlertRead(alertId: string) {
  const res = await apiClient.post(`/alerts/${alertId}/read`)
  return res.data
}

export async function dismissAlert(alertId: string) {
  const res = await apiClient.post(`/alerts/${alertId}/dismiss`)
  return res.data
}
