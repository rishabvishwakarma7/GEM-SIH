import apiClient from './client'
import type {
  BidderDocumentType,
  BidderDocumentDetail,
  BidderDocumentStatusResponse,
} from '../types'

export async function uploadBidderDocument(
  bidderId: string,
  documentType: BidderDocumentType,
  file: File,
  onProgress?: (percent: number) => void
): Promise<{ message: string; filename: string; document_id: string; processing_status: string }> {
  const formData = new FormData()
  formData.append('bidder_id', bidderId)
  formData.append('document_type', documentType)
  formData.append('file', file)

  const res = await apiClient.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded / evt.total) * 100))
      }
    },
  })
  return res.data
}

export async function processBidderDocument(documentId: string): Promise<BidderDocumentStatusResponse> {
  const res = await apiClient.post<BidderDocumentStatusResponse>(`/documents/${documentId}/process`)
  return res.data
}

export async function getBidderDocumentStatus(documentId: string): Promise<BidderDocumentStatusResponse> {
  const res = await apiClient.get<BidderDocumentStatusResponse>(`/documents/${documentId}/status`)
  return res.data
}

export async function getBidderDocument(documentId: string): Promise<BidderDocumentDetail> {
  const res = await apiClient.get<BidderDocumentDetail>(`/documents/${documentId}`)
  return res.data
}
