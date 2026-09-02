import uuid
from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, ConfigDict

from app.models.compliance import ComplianceStatus, RiskLevel


class RequirementResultOut(BaseModel):
    requirement_id: str
    requirement: str
    category: str
    mandatory: bool
    required_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    status: str  # "COMPLIANT" | "NON_COMPLIANT" | "NEEDS_REVIEW"
    reason: str
    evidence: Optional[str] = None
    source_document: Optional[str] = None
    verification_provider: Optional[str] = None
    clause_reference: Optional[str] = None


class ComplianceResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tender_id: uuid.UUID
    bidder_id: uuid.UUID
    overall_status: ComplianceStatus
    risk_level: RiskLevel
    compliance_score: float
    mandatory_failed: bool
    explanation: Optional[str] = None
    ai_recommendation: Optional[str] = None
    total_requirements: str
    compliant_count: str
    non_compliant_count: str
    needs_review_count: str
    evaluated_at: datetime


class ComplianceResultDetailOut(ComplianceResultOut):
    requirement_results: List[RequirementResultOut] = []


class BidderComparisonEntry(BaseModel):
    bidder_id: str
    company_name: str
    compliance_score: float
    overall_status: str
    risk_level: str
    mandatory_failed: bool
    compliant_count: int
    non_compliant_count: int
    needs_review_count: int
    total_requirements: int
    evaluated_at: datetime


class BidderComparisonOut(BaseModel):
    tender_id: str
    bidders: List[BidderComparisonEntry]
