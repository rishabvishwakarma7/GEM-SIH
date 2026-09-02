import apiClient from './client'
import type { Notification } from '../types'

export async function listBidderNotifications(bidderId: string): Promise<Notification[]> {
  const res = await apiClient.get<Notification[]>(`/notifications/bidder/${bidderId}`)
  return res.data
}

export async function sendBidderAlert(bidderId: string): Promise<Notification> {
  const res = await apiClient.post<Notification>(`/notifications/bidder/${bidderId}/send`)
  return res.data
}
