import apiClient from './client'

export interface RiskFactor {
  factor: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  score_contribution: number
  detail: string
}

export interface RiskBreakdown {
  compliance_failures: number
  government_mismatches: number
  suspicious_documents: number
  missing_documents: number
  identity_inconsistency: number
  duplicate_documents: number
}

export interface BidderRisk {
  bidder_id: string
  company_name: string
  risk_score: number
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  factors: RiskFactor[]
  breakdown: RiskBreakdown
  ai_summary: string | null
  analyzed_at: string | null
}

export interface RiskTimelineEvent {
  timestamp: string | null
  action: string
  entity_type: string
  entity_id: string | null
  details: Record<string, unknown>
}

export interface SuspicionSignal {
  signal: string
  weight: number
  detail: string
}

export interface DocumentRisk {
  id: string
  bidder_document_id: string
  risk_score: number
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  suspicious: boolean
  suspicion_signals: SuspicionSignal[]
  metadata_anomaly: boolean
  date_inconsistency: boolean
  identifier_mismatch: boolean
  registry_mismatch: boolean
  low_ai_confidence: boolean
  type_mismatch_flag: boolean
  pdf_creation_date: string | null
  pdf_modification_date: string | null
  pdf_producer: string | null
  pdf_author: string | null
  ai_risk_summary: string | null
  analyzed_at: string | null
}

export interface DuplicateMatch {
  id: string
  source_document_id: string
  target_document_id: string
  source_bidder_id: string
  target_bidder_id: string
  tender_id: string
  similarity_score: number
  match_type: 'exact' | 'high_similarity' | 'possible_similarity' | 'low_similarity'
  exact_hash_match: boolean
  reviewed: boolean
  reviewed_by: string | null
  reviewed_at: string | null
  review_notes: string | null
  detected_at: string | null
}

export interface EvidenceStep {
  step: string
  label: string
  value: string | null
  detail: string | null
  status: string | null
}

export interface RequirementEvidence {
  requirement_id: string
  requirement_title: string
  category: string
  mandatory: boolean
  status: string
  reason_code: string
  required_value: string
  actual_value: string
  confidence: number | null
  human_review_required: boolean
  evidence: { document_name: string | null; snippet: string | null; page_number: number | null } | null
  verification: { provider: string | null; status: string | null } | null
  evidence_chain: EvidenceStep[]
}

export interface BidderEvidence {
  bidder_id: string
  company_name: string
  tender_id: string
  overall_status: string
  compliance_score: number
  requirement_results: RequirementEvidence[]
}

export interface FinalDecision {
  id: string
  case_id: string
  bidder_id: string
  tender_id: string
  decision: 'qualified' | 'disqualified' | 'clarification_required'
  officer_id: string
  officer_remarks: string
  version: number
  superseded: boolean
  submitted_at: string
}

export async function getBidderRisk(bidderId: string): Promise<BidderRisk> {
  const res = await apiClient.get<BidderRisk>(`/bidders/${bidderId}/risk`)
  return res.data
}

export async function analyzeBidderRisk(bidderId: string): Promise<BidderRisk> {
  const res = await apiClient.post<BidderRisk>(`/bidders/${bidderId}/risk/analyze`)
  return res.data
}

export async function getBidderRiskTimeline(bidderId: string): Promise<{ bidder_id: string; events: RiskTimelineEvent[] }> {
  const res = await apiClient.get(`/bidders/${bidderId}/risk/timeline`)
  return res.data
}

export async function getBidderEvidence(bidderId: string): Promise<BidderEvidence> {
  const res = await apiClient.get<BidderEvidence>(`/bidders/${bidderId}/evidence`)
  return res.data
}

export async function getRequirementEvidence(requirementId: string, bidderId: string) {
  const res = await apiClient.get(`/requirements/${requirementId}/evidence`, { params: { bidder_id: bidderId } })
  return res.data
}

export async function getDocumentRisk(documentId: string): Promise<DocumentRisk> {
  const res = await apiClient.get<DocumentRisk>(`/documents/${documentId}/risk`)
  return res.data
}

export async function analyzeDocumentRisk(documentId: string): Promise<DocumentRisk> {
  const res = await apiClient.post<DocumentRisk>(`/documents/${documentId}/risk/analyze`)
  return res.data
}

export async function getDuplicateMatches(params: {
  tender_id?: string
  bidder_id?: string
  reviewed?: boolean
  page?: number
  page_size?: number
}): Promise<DuplicateMatch[]> {
  const res = await apiClient.get<DuplicateMatch[]>('/documents/duplicates', { params })
  return res.data
}

export async function reviewDuplicateMatch(matchId: string, reviewed: boolean, review_notes?: string) {
  const res = await apiClient.post(`/documents/duplicates/${matchId}/review`, { reviewed, review_notes })
  return res.data
}

export async function getFinalDecision(bidderId: string): Promise<FinalDecision> {
  const res = await apiClient.get<FinalDecision>(`/bidders/${bidderId}/final-decision`)
  return res.data
}

export async function submitFinalDecision(bidderId: string, decision: string, officer_remarks: string): Promise<FinalDecision> {
  const res = await apiClient.post<FinalDecision>(`/bidders/${bidderId}/final-decision`, { decision, officer_remarks })
  return res.data
}

export async function getDecisionHistory(bidderId: string): Promise<FinalDecision[]> {
  const res = await apiClient.get<FinalDecision[]>(`/bidders/${bidderId}/final-decision/history`)
  return res.data
}
