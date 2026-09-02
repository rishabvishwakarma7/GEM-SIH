"""Pydantic schemas for multi-level review workflow and final decisions."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Review Case
# ---------------------------------------------------------------------------

class ReviewActionOut(BaseModel):
    id: str
    case_id: str
    action_type: str
    actor_id: str
    actor_role: Optional[str] = None
    notes: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewCaseOut(BaseModel):
    id: str
    tender_id: str
    bidder_id: str
    status: str
    priority: str
    review_level: str
    reason: Optional[str] = None
    trigger_events: Optional[List[str]] = None
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    actions: List[ReviewActionOut] = []

    model_config = {"from_attributes": True}


class ReviewCaseListOut(BaseModel):
    items: List[ReviewCaseOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# Review Actions (request bodies)
# ---------------------------------------------------------------------------

class AssignCaseRequest(BaseModel):
    assigned_to: str   # user_id


class ReviewActionRequest(BaseModel):
    action_type: str   # ReviewActionType value
    notes: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class EscalateRequest(BaseModel):
    target_level: str   # ReviewLevel value
    reason: str


# ---------------------------------------------------------------------------
# Final Decision
# ---------------------------------------------------------------------------

class FinalDecisionOut(BaseModel):
    id: str
    case_id: str
    bidder_id: str
    tender_id: str
    decision: str
    officer_id: str
    officer_remarks: str
    version: int
    superseded: bool
    submitted_at: datetime

    model_config = {"from_attributes": True}


class FinalDecisionRequest(BaseModel):
    decision: str      # FinalDecisionType value
    officer_remarks: str

    @field_validator("officer_remarks")
    @classmethod
    def remarks_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Officer remarks are mandatory for a final decision")
        return v.strip()

    @field_validator("decision")
    @classmethod
    def valid_decision(cls, v: str) -> str:
        valid = {"qualified", "disqualified", "clarification_required"}
        if v.lower() not in valid:
            raise ValueError(f"Decision must be one of: {', '.join(valid)}")
        return v.lower()


# ---------------------------------------------------------------------------
# Evidence chain (explainable compliance)
# ---------------------------------------------------------------------------

class EvidenceStep(BaseModel):
    step: str
    label: str
    value: Optional[str] = None
    detail: Optional[str] = None
    status: Optional[str] = None


class RequirementEvidenceOut(BaseModel):
    requirement_id: str
    requirement_title: str
    category: str
    mandatory: bool
    status: str
    reason_code: str
    required_value: Optional[str] = None
    actual_value: Optional[str] = None
    confidence: Optional[float] = None
    human_review_required: bool
    evidence: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    evidence_chain: List[EvidenceStep] = []


class BidderEvidenceOut(BaseModel):
    bidder_id: str
    company_name: str
    tender_id: str
    overall_status: str
    compliance_score: float
    requirement_results: List[RequirementEvidenceOut] = []
