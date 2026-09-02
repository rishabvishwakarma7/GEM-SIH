import apiClient from './client'
import type {
  Tender,
  TenderDetail,
  TenderRequirement,
  TenderStatusResponse,
} from '../types'

export interface CreateTenderPayload {
  tender_ref_no: string
  title: string
  department?: string
  description?: string
  tender_date?: string
  deadline?: string
}

export async function listTenders(): Promise<Tender[]> {
  const res = await apiClient.get<Tender[]>('/tenders/')
  return res.data
}

export async function createTender(payload: CreateTenderPayload): Promise<Tender> {
  const res = await apiClient.post<Tender>('/tenders/', payload)
  return res.data
}

export async function getTender(tenderId: string): Promise<TenderDetail> {
  const res = await apiClient.get<TenderDetail>(`/tenders/${tenderId}`)
  return res.data
}

export async function uploadTenderDocument(
  tenderId: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<{ message: string; filename: string; processing_status: string }> {
  const formData = new FormData()
  formData.append('file', file)

  const res = await apiClient.post(`/tenders/${tenderId}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded / evt.total) * 100))
      }
    },
  })
  return res.data
}

export async function processTender(tenderId: string): Promise<TenderStatusResponse> {
  const res = await apiClient.post<TenderStatusResponse>(`/tenders/${tenderId}/process`)
  return res.data
}

export async function getTenderStatus(tenderId: string): Promise<TenderStatusResponse> {
  const res = await apiClient.get<TenderStatusResponse>(`/tenders/${tenderId}/status`)
  return res.data
}

export async function listTenderRequirements(tenderId: string): Promise<TenderRequirement[]> {
  const res = await apiClient.get<TenderRequirement[]>(`/tenders/${tenderId}/requirements`)
  return res.data
}

export async function getTenderRequirement(
  tenderId: string,
  requirementId: string
): Promise<TenderRequirement> {
  const res = await apiClient.get<TenderRequirement>(
    `/tenders/${tenderId}/requirements/${requirementId}`
  )
  return res.data
}
