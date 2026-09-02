import apiClient from './client'
import type { ComplianceResultDetail, BidderComparison, BatchEvaluateSummary } from '../types'

export async function evaluateBidderCompliance(bidderId: string): Promise<ComplianceResultDetail> {
  const res = await apiClient.post<ComplianceResultDetail>(`/compliance/bidder/${bidderId}/evaluate`)
  return res.data
}

export async function getBidderCompliance(bidderId: string): Promise<ComplianceResultDetail | null> {
  try {
    const res = await apiClient.get<ComplianceResultDetail>(`/compliance/bidder/${bidderId}`)
    return res.data
  } catch (err: any) {
    if (err?.response?.status === 404) return null
    throw err
  }
}

export async function getTenderComparison(tenderId: string): Promise<BidderComparison> {
  const res = await apiClient.get<BidderComparison>(`/compliance/tender/${tenderId}/comparison`)
  return res.data
}

// Bulk/batch operation (Day 6): verify + evaluate every bidder under a
// tender in one call, instead of doing it one bidder at a time.
export async function batchEvaluateTender(tenderId: string): Promise<BatchEvaluateSummary> {
  const res = await apiClient.post<BatchEvaluateSummary>(`/compliance/tender/${tenderId}/batch-evaluate`)
  return res.data
}
