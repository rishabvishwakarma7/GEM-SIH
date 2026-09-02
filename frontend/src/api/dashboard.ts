import apiClient from './client'
import type { DashboardStats, DashboardBidderRow, PaginatedResponse } from '../types'

export async function getDashboardStats(): Promise<DashboardStats> {
  const res = await apiClient.get<DashboardStats>('/dashboard/stats')
  return res.data
}

export interface DashboardBidderQuery {
  search?: string
  status?: string
  tender_id?: string
  sort_by?: 'company_name' | 'compliance_score' | 'status'
  sort_dir?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export async function getDashboardBidders(
  query: DashboardBidderQuery
): Promise<PaginatedResponse<DashboardBidderRow>> {
  const res = await apiClient.get<PaginatedResponse<DashboardBidderRow>>('/dashboard/bidders', {
    params: query,
  })
  return res.data
}
