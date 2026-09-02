import apiClient from './client'
import type { Bidder, BidderDetail, BidderConsistencyReport } from '../types'

export interface CreateBidderPayload {
  tender_id: string
  company_name: string
  gem_seller_id?: string
  contact_email?: string
  contact_phone?: string
}

export async function listBidders(tenderId?: string): Promise<Bidder[]> {
  const res = await apiClient.get<Bidder[]>('/bidders/', {
    params: tenderId ? { tender_id: tenderId } : undefined,
  })
  return res.data
}

export async function createBidder(payload: CreateBidderPayload): Promise<Bidder> {
  const res = await apiClient.post<Bidder>('/bidders/', payload)
  return res.data
}

export async function getBidder(bidderId: string): Promise<BidderDetail> {
  const res = await apiClient.get<BidderDetail>(`/bidders/${bidderId}`)
  return res.data
}

export async function analyzeBidder(bidderId: string): Promise<BidderConsistencyReport> {
  const res = await apiClient.post<BidderConsistencyReport>(`/bidders/${bidderId}/analyze`)
  return res.data
}
