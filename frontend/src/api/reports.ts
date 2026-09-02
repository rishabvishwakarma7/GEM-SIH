import apiClient from './client'
import type { ReportRecord } from '../types'

function triggerDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}

function filenameFromDisposition(disposition: string | undefined, fallback: string): string {
  if (!disposition) return fallback
  const match = disposition.match(/filename="?([^"]+)"?/)
  return match ? match[1] : fallback
}

export async function downloadBidderReportPdf(bidderId: string, companyName: string): Promise<void> {
  const res = await apiClient.get(`/reports/bidder/${bidderId}/pdf`, { responseType: 'blob' })
  const filename = filenameFromDisposition(
    res.headers['content-disposition'],
    `compliance_report_${companyName}.pdf`
  )
  triggerDownload(res.data, filename)
}

export async function downloadBidderReportCsv(bidderId: string, companyName: string): Promise<void> {
  const res = await apiClient.get(`/reports/bidder/${bidderId}/csv`, { responseType: 'blob' })
  const filename = filenameFromDisposition(
    res.headers['content-disposition'],
    `compliance_report_${companyName}.csv`
  )
  triggerDownload(res.data, filename)
}

export async function listTenderReports(tenderId: string): Promise<ReportRecord[]> {
  const res = await apiClient.get<ReportRecord[]>(`/reports/tender/${tenderId}`)
  return res.data
}

export async function downloadReportById(reportId: string, filename: string): Promise<void> {
  const res = await apiClient.get(`/reports/download/${reportId}`, { responseType: 'blob' })
  triggerDownload(res.data, filename)
}
