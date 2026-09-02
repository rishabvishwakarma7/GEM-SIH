import apiClient from './client'

export interface ReviewAction {
  id: string
  case_id: string
  action_type: string
  actor_id: string
  actor_role: string | null
  notes: string | null
  details: Record<string, unknown> | null
  created_at: string
}

export interface ReviewCase {
  id: string
  tender_id: string
  bidder_id: string
  status: 'open' | 'assigned' | 'in_review' | 'escalated' | 'approved' | 'rejected' | 'clarification_required' | 'closed'
  priority: 'low' | 'medium' | 'high' | 'critical'
  review_level: 'evaluator' | 'senior_evaluator' | 'procurement_officer'
  reason: string | null
  trigger_events: string[] | null
  assigned_to: string | null
  assigned_at: string | null
  created_at: string
  reviewed_at: string | null
  resolved_at: string | null
  actions: ReviewAction[]
}

export interface ReviewListResponse {
  items: ReviewCase[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export async function listReviewCases(params: {
  status?: string
  priority?: string
  review_level?: string
  tender_id?: string
  bidder_id?: string
  assigned_to?: string
  page?: number
  page_size?: number
}): Promise<ReviewListResponse> {
  const res = await apiClient.get<ReviewListResponse>('/reviews/', { params })
  return res.data
}

export async function getReviewCase(caseId: string): Promise<ReviewCase> {
  const res = await apiClient.get<ReviewCase>(`/reviews/${caseId}`)
  return res.data
}

export async function createReviewCase(bidderId: string, reason: string, priority = 'medium'): Promise<ReviewCase> {
  const res = await apiClient.post<ReviewCase>('/reviews/', null, {
    params: { bidder_id: bidderId, reason, priority },
  })
  return res.data
}

export async function assignReviewCase(caseId: string, assignedTo: string): Promise<ReviewCase> {
  const res = await apiClient.post(`/reviews/${caseId}/assign`, { assigned_to: assignedTo })
  return res.data
}

export async function addReviewAction(
  caseId: string,
  actionType: string,
  notes?: string,
  details?: Record<string, unknown>
): Promise<ReviewCase> {
  const res = await apiClient.post(`/reviews/${caseId}/action`, {
    action_type: actionType,
    notes,
    details,
  })
  return res.data
}

export async function escalateReviewCase(caseId: string, targetLevel: string, reason: string): Promise<ReviewCase> {
  const res = await apiClient.post(`/reviews/${caseId}/escalate`, {
    target_level: targetLevel,
    reason,
  })
  return res.data
}
