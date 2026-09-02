"""Pydantic schemas for risk intelligence, duplicate detection."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SuspicionSignal(BaseModel):
    signal: str
    weight: int
    detail: str


class DocumentRiskOut(BaseModel):
    id: str
    bidder_document_id: str
    risk_score: float
    risk_level: str
    suspicious: bool
    suspicion_signals: List[SuspicionSignal] = []
    metadata_anomaly: bool
    date_inconsistency: bool
    identifier_mismatch: bool
    registry_mismatch: bool
    low_ai_confidence: bool
    type_mismatch_flag: bool
    pdf_creation_date: Optional[str] = None
    pdf_modification_date: Optional[str] = None
    pdf_producer: Optional[str] = None
    pdf_author: Optional[str] = None
    ai_risk_summary: Optional[str] = None
    analyzed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DuplicateMatchOut(BaseModel):
    id: str
    source_document_id: str
    target_document_id: str
    source_bidder_id: str
    target_bidder_id: str
    tender_id: str
    similarity_score: float
    match_type: str
    exact_hash_match: bool
    reviewed: bool
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    detected_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RiskFactor(BaseModel):
    factor: str
    severity: str
    score_contribution: float
    detail: str


class RiskBreakdown(BaseModel):
    compliance_failures: float = 0
    government_mismatches: float = 0
    suspicious_documents: float = 0
    missing_documents: float = 0
    identity_inconsistency: float = 0
    duplicate_documents: float = 0


class BidderRiskOut(BaseModel):
    bidder_id: str
    company_name: str
    risk_score: float
    risk_level: str
    factors: List[RiskFactor] = []
    breakdown: RiskBreakdown
    ai_summary: Optional[str] = None
    analyzed_at: Optional[str] = None


class RiskTimelineEvent(BaseModel):
    timestamp: Optional[str]
    action: str
    entity_type: str
    entity_id: Optional[str]
    details: Dict[str, Any] = {}


class DuplicateReviewRequest(BaseModel):
    reviewed: bool
    review_notes: Optional[str] = None
