export type UserRole = 'admin' | 'evaluator' | 'viewer'

export interface User {
  id: string
  full_name: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export type TenderStatus = 'draft' | 'open' | 'under_evaluation' | 'closed'

export type ProcessingStatus =
  | 'pending'
  | 'uploaded'
  | 'extracting_text'
  | 'text_extracted'
  | 'extracting_requirements'
  | 'completed'
  | 'failed'

export interface Tender {
  id: string
  tender_ref_no: string
  title: string
  department?: string | null
  description?: string | null
  tender_date?: string | null
  deadline?: string | null
  organization: string
  status: TenderStatus
  document_path?: string | null
  extraction_method?: string | null
  page_count?: number | null
  processing_status: ProcessingStatus
  processing_error?: string | null
  created_at: string
  updated_at: string
}

export type RequirementCategory =
  | 'identity'
  | 'pan'
  | 'gst'
  | 'udyam_msme'
  | 'company_registration'
  | 'financial'
  | 'turnover'
  | 'income_tax'
  | 'startup_dpiit'
  | 'nsic'
  | 'epfo'
  | 'esic'
  | 'blacklist_debarment'
  | 'digilocker'
  | 'bis'
  | 'make_in_india'
  | 'other'

export type VerificationType = 'document' | 'threshold' | 'declaration' | 'database_check' | 'other'

export interface TenderRequirement {
  id: string
  tender_id: string
  category: RequirementCategory
  title: string
  description: string
  clause_reference?: string | null
  minimum_value?: number | null
  currency?: string | null
  period?: string | null
  mandatory: boolean
  required_documents?: string[] | null
  verification_type: VerificationType
  confidence?: number | null
  evidence?: string | null
  page_number?: number | null
  needs_review: boolean
  extracted_by_ai: boolean
  sequence_no: number
  created_at: string
}

export interface TenderDetail extends Tender {
  requirements: TenderRequirement[]
}

export interface TenderStatusResponse {
  processing_status: ProcessingStatus
  processing_error?: string | null
  requirements_count: number
  page_count?: number | null
  extraction_method?: string | null
}

export const REQUIREMENT_CATEGORY_LABELS: Record<RequirementCategory, string> = {
  identity: 'Identity',
  pan: 'PAN',
  gst: 'GST',
  udyam_msme: 'Udyam / MSME',
  company_registration: 'Company Registration',
  financial: 'Financial',
  turnover: 'Turnover',
  income_tax: 'Income Tax',
  startup_dpiit: 'Startup / DPIIT',
  nsic: 'NSIC',
  epfo: 'EPFO',
  esic: 'ESIC',
  blacklist_debarment: 'Blacklist / Debarment',
  digilocker: 'DigiLocker',
  bis: 'BIS',
  make_in_india: 'Make in India',
  other: 'Other',
}

export const PROCESSING_STATUS_LABELS: Record<ProcessingStatus, string> = {
  pending: 'Not Started',
  uploaded: 'Document Uploaded',
  extracting_text: 'Extracting Text...',
  text_extracted: 'Text Extracted',
  extracting_requirements: 'AI Analyzing Requirements...',
  completed: 'Completed',
  failed: 'Failed',
}

// ---------------------------------------------------------------------------
// Bidder Document Intelligence (Day 3)
// ---------------------------------------------------------------------------

export type BidderDocumentType =
  | 'pan'
  | 'gst'
  | 'udyam_msme'
  | 'company_registration'
  | 'income_tax'
  | 'startup_dpiit'
  | 'nsic'
  | 'epfo'
  | 'esic'
  | 'digilocker'
  | 'bis'
  | 'financial_statement'
  | 'turnover_certificate'
  | 'make_in_india'
  | 'other'

export const BIDDER_DOCUMENT_TYPE_LABELS: Record<BidderDocumentType, string> = {
  pan: 'PAN',
  gst: 'GST Certificate',
  udyam_msme: 'Udyam / MSME Certificate',
  company_registration: 'MCA / Company Registration',
  income_tax: 'Income Tax Document',
  startup_dpiit: 'Startup / DPIIT Certificate',
  nsic: 'NSIC Document',
  epfo: 'EPFO Document',
  esic: 'ESIC Document',
  digilocker: 'DigiLocker Document',
  bis: 'BIS Certificate',
  financial_statement: 'Financial Statement',
  turnover_certificate: 'Turnover Certificate',
  make_in_india: 'Make in India / Local Content Document',
  other: 'Other',
}

export type DocumentProcessingStatus =
  | 'uploaded'
  | 'extracting_text'
  | 'text_extracted'
  | 'extracting_data'
  | 'completed'
  | 'failed'

export const DOCUMENT_PROCESSING_STATUS_LABELS: Record<DocumentProcessingStatus, string> = {
  uploaded: 'Uploaded',
  extracting_text: 'Extracting Text...',
  text_extracted: 'Text Extracted',
  extracting_data: 'AI Classifying & Extracting...',
  completed: 'Completed',
  failed: 'Failed',
}

export type BidderConsistencyStatus = 'not_analyzed' | 'consistent' | 'needs_review' | 'inconsistent'

export const BIDDER_CONSISTENCY_STATUS_LABELS: Record<BidderConsistencyStatus, string> = {
  not_analyzed: 'Not Analyzed',
  consistent: 'Consistent',
  needs_review: 'Needs Review',
  inconsistent: 'Inconsistent',
}

export interface ExtractedDocumentData {
  detected_document_type?: string | null
  classification_confidence?: number | null
  type_mismatch: boolean
  structured_fields?: Record<string, any> | null
  missing_fields?: string[] | null
  confidence?: number | null
  evidence?: string | null
  page_number?: number | null
  is_readable: boolean
  needs_review: boolean
  extracted_at: string
}

export interface BidderDocument {
  id: string
  bidder_id: string
  document_type: BidderDocumentType
  original_filename: string
  file_kind: string
  uploaded_at: string
  extraction_method?: string | null
  page_count?: number | null
  processing_status: DocumentProcessingStatus
  processing_error?: string | null
}

export interface BidderDocumentDetail extends BidderDocument {
  extracted_data?: ExtractedDocumentData | null
}

export interface BidderDocumentStatusResponse {
  document_id: string
  processing_status: DocumentProcessingStatus
  processing_error?: string | null
  page_count?: number | null
  extraction_method?: string | null
}

export interface IdentityWarning {
  field: string
  message: string
  documents: string[]
}

export interface BidderConsistencyReport {
  missing_documents: string[]
  identity_warnings: IdentityWarning[]
  documents_analyzed: number
  documents_failed: number
  documents_needing_review: number
}

export interface Bidder {
  id: string
  tender_id: string
  company_name: string
  gem_seller_id?: string | null
  contact_email?: string | null
  contact_phone?: string | null
  consistency_status: BidderConsistencyStatus
  missing_document_types?: string[] | null
  analyzed_at?: string | null
  created_at: string
  updated_at: string
}

export interface BidderDetail extends Bidder {
  documents: BidderDocumentDetail[]
  consistency_report?: BidderConsistencyReport | null
  // Upgrade: risk intelligence fields
  risk_score?: number | null
  risk_level?: string | null
  risk_summary?: string | null
  risk_analyzed_at?: string | null
}

// ---------------------------------------------------------------------------
// Verification & Compliance (Day 4)
// ---------------------------------------------------------------------------

export type VerificationStatus = 'verified' | 'mismatch' | 'not_found' | 'pending'

export const VERIFICATION_STATUS_LABELS: Record<VerificationStatus, string> = {
  verified: 'Verified',
  mismatch: 'Mismatch',
  not_found: 'Not Found',
  pending: 'Pending',
}

export interface VerificationResult {
  id: string
  bidder_id: string
  requirement_id: string
  bidder_document_id?: string | null
  status: VerificationStatus
  provider_name?: string | null
  identifier_checked?: string | null
  raw_response?: Record<string, any> | null
  is_mock: boolean
  evidence_snippet?: string | null
  notes?: string | null
  verified_at: string
}

export type RequirementResultStatus = 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW'

export interface RequirementResult {
  requirement_id: string
  requirement: string
  category: RequirementCategory
  mandatory: boolean
  required_value?: any
  actual_value?: any
  status: RequirementResultStatus
  reason: string
  evidence?: string | null
  source_document?: string | null
  verification_provider?: string | null
  clause_reference?: string | null
}

export type ComplianceStatus = 'compliant' | 'non_compliant' | 'needs_review'
export type RiskLevel = 'low' | 'medium' | 'high'

export const COMPLIANCE_STATUS_LABELS: Record<ComplianceStatus, string> = {
  compliant: 'Compliant',
  non_compliant: 'Non-Compliant',
  needs_review: 'Needs Review',
}

export interface ComplianceResult {
  id: string
  tender_id: string
  bidder_id: string
  overall_status: ComplianceStatus
  risk_level: RiskLevel
  compliance_score: number
  mandatory_failed: boolean
  explanation?: string | null
  ai_recommendation?: string | null
  total_requirements: string
  compliant_count: string
  non_compliant_count: string
  needs_review_count: string
  evaluated_at: string
}

export interface ComplianceResultDetail extends ComplianceResult {
  requirement_results: RequirementResult[]
}

export interface BidderComparisonEntry {
  bidder_id: string
  company_name: string
  gem_seller_id?: string | null
  compliance_score: number
  overall_status: string
  risk_level: string
  mandatory_failed: boolean
  compliant_count: number
  non_compliant_count: number
  needs_review_count: number
  total_requirements: number
  evaluated_at: string
  // Upgrade columns
  risk_score?: number | null
  bidder_risk_level?: string | null
  suspicious_document_count?: number
  duplicate_document_count?: number
  document_completeness?: number
  identity_consistency?: string
  review_status?: string
  review_level?: string | null
  ai_recommendation?: string | null
}

export interface BidderComparison {
  tender_id: string
  bidders: BidderComparisonEntry[]
}

// ---------------------------------------------------------------------------
// Notifications (Day 6)
// ---------------------------------------------------------------------------

export type NotificationChannel = 'email' | 'sms'
export type NotificationDeliveryStatus = 'sent' | 'failed' | 'skipped'

export interface Notification {
  id: string
  bidder_id: string
  tender_id?: string | null
  channel: NotificationChannel
  status: NotificationDeliveryStatus
  recipient?: string | null
  subject?: string | null
  message: string
  reason?: string | null
  created_at: string
}

// ---------------------------------------------------------------------------
// Batch / bulk operations (Day 6)
// ---------------------------------------------------------------------------

export interface BatchEvaluateBidderResult {
  bidder_id: string
  company_name: string
  success: boolean
  overall_status?: string
  compliance_score?: number
  risk_level?: string
  error?: string
}

export interface BatchEvaluateSummary {
  tender_id: string
  bidders_processed: number
  results: BatchEvaluateBidderResult[]
}

// ---------------------------------------------------------------------------
// Dashboard, Reports, Audit (Day 5)
// ---------------------------------------------------------------------------

export interface DashboardStats {
  total_tenders: number
  total_bidders: number
  compliant_bidders: number
  non_compliant_bidders: number
  needs_review_bidders: number
  average_compliance_score: number | null
  evaluated_bidders: number
}

export interface DashboardBidderRow {
  bidder_id: string
  company_name: string
  gem_seller_id?: string | null
  tender_id: string
  tender_ref_no: string
  compliance_score: number | null
  status: 'compliant' | 'non_compliant' | 'needs_review' | 'not_evaluated'
  risk_level: string | null
  failed_requirements: number
  review_items: number
  evaluated_at: string | null
}

export interface PaginatedResponse<T> {
  items: T[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface ReportRecord {
  id: string
  tender_id: string
  file_path: string
  report_type: string
  generated_at: string
}

export interface AuditLogEntry {
  id: string
  user_id?: string | null
  user_name?: string | null
  action: string
  entity_type?: string | null
  entity_id?: string | null
  details?: string | null
  created_at: string
}
