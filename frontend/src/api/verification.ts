import apiClient from './client'
import type { VerificationResult } from '../types'

export async function runVerification(bidderId: string): Promise<{ bidder_id: string; checks_run: number; results: VerificationResult[] }> {
  const res = await apiClient.post(`/verification/bidder/${bidderId}/run`)
  return res.data
}

export async function listVerificationResults(bidderId: string): Promise<VerificationResult[]> {
  const res = await apiClient.get<VerificationResult[]>(`/verification/bidder/${bidderId}`)
  return res.data
}
