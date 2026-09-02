"""
Bidder risk intelligence, evidence chain, and final decision routes (Upgrade — Tasks 9).

GET  /api/bidders/{id}/risk              — current risk profile
POST /api/bidders/{id}/risk/analyze      — recompute risk
GET  /api/bidders/{id}/risk/timeline     — chronological event timeline
GET  /api/bidders/{id}/evidence          — full evidence chain for all requirements
GET  /api/requirements/{req_id}/evidence — evidence for a single requirement
POST /api/bidders/{id}/final-decision    — procurement officer submits final decision
GET  /api/bidders/{id}/final-decision    — get current (latest) final decision
"""
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.bidder import Bidder
from app.models.compliance import ComplianceResult
from app.models.review import ReviewCase, ReviewStatus, FinalDecision, FinalDecisionType
from app.models.verification import VerificationResult
from app.models.tender import TenderRequirement
from app.schemas.risk import BidderRiskOut, RiskFactor, RiskBreakdown, RiskTimelineEvent
from app.schemas.review import FinalDecisionOut, FinalDecisionRequest, BidderEvidenceOut
from app.core.deps import get_current_user, require_roles
from app.services.risk_intelligence_service import analyze_bidder_risk, build_risk_timeline
from app.services.audit_service import log_action
from app.core.logging_config import logger

router = APIRouter(tags=["risk-intelligence"])


# ---------------------------------------------------------------------------
# Helper: map reason to human-readable reason_code
# ---------------------------------------------------------------------------
def _reason_code(result: dict) -> str:
    status = result.get("status", "")
    reason = (result.get("reason") or "").lower()
    if status == "NON_COMPLIANT":
        if "threshold" in reason or "below" in reason:
            return "THRESHOLD_NOT_MET"
        if "document" in reason and "found" in reason:
            return "DOCUMENT_MISSING"
        if "registry" in reason or "mismatch" in reason:
            return "REGISTRY_VERIFICATION_FAILED"
        if "not found" in reason:
            return "REGISTRY_NOT_FOUND"
        return "MANDATORY_REQUIREMENT_FAILED"
    if status == "NEEDS_REVIEW":
        if "confidence" in reason:
            return "LOW_AI_CONFIDENCE"
        if "document" in reason:
            return "DOCUMENT_MISSING"
        if "readable" in reason or "unreadable" in reason:
            return "DOCUMENT_UNREADABLE"
        if "identity" in reason or "mismatch" in reason:
            return "IDENTITY_MISMATCH"
        return "MANUAL_REVIEW_REQUIRED"
    return "COMPLIANT"


def _build_evidence_chain(req_result: dict, verifications: List[VerificationResult]) -> list:
    """Builds ordered evidence chain steps for one requirement result."""
    chain = []
    chain.append({
        "step": "clause",
        "label": "Tender Clause",
        "value": req_result.get("clause_reference", "—"),
        "detail": None,
        "status": None,
    })
    chain.append({
        "step": "requirement",
        "label": "Requirement",
        "value": req_result.get("requirement", ""),
        "detail": f"Required: {req_result.get('required_value', '—')}",
        "status": None,
    })
    chain.append({
        "step": "document",
        "label": "Expected Document",
        "value": req_result.get("source_document") or "Not uploaded",
        "detail": None,
        "status": "found" if req_result.get("source_document") else "missing",
    })
    chain.append({
        "step": "extraction",
        "label": "Extracted Value",
        "value": str(req_result.get("actual_value") or "—"),
        "detail": req_result.get("evidence") or "No evidence snippet",
        "status": None,
    })
    vr_match = next(
        (v for v in verifications if str(v.requirement_id) == req_result.get("requirement_id")),
        None,
    )
    if vr_match:
        chain.append({
            "step": "verification",
            "label": "Government Verification",
            "value": f"{vr_match.provider_name} — {vr_match.status.value.upper()}",
            "detail": vr_match.notes or "",
            "status": vr_match.status.value,
        })
    chain.append({
        "step": "rule",
        "label": "Rule Evaluation",
        "value": f"Deterministic rule → {req_result.get('status', '—')}",
        "detail": req_result.get("reason", ""),
        "status": req_result.get("status", "").lower(),
    })
    chain.append({
        "step": "verdict",
        "label": "Final Requirement Verdict",
        "value": req_result.get("status", "—"),
        "detail": "Mandatory" if req_result.get("mandatory") else "Optional",
        "status": req_result.get("status", "").lower(),
    })
    return chain


# ---------------------------------------------------------------------------
# Risk endpoints
# ---------------------------------------------------------------------------

@router.get("/api/bidders/{bidder_id}/risk")
def get_bidder_risk(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    if bidder.risk_score is None:
        raise HTTPException(
            status_code=404,
            detail="Risk analysis not yet run — call POST /risk/analyze",
        )

    try:
        factors = json.loads(bidder.risk_factors or "[]")
    except (json.JSONDecodeError, TypeError):
        factors = []

    compliance = db.query(ComplianceResult).filter(ComplianceResult.bidder_id == bidder_id).first()
    breakdown = {}
    if compliance and compliance.risk_breakdown:
        try:
            breakdown = json.loads(compliance.risk_breakdown)
        except (json.JSONDecodeError, TypeError):
            breakdown = {}

    return {
        "bidder_id": str(bidder_id),
        "company_name": bidder.company_name,
        "risk_score": bidder.risk_score,
        "risk_level": bidder.risk_level,
        "factors": factors,
        "breakdown": breakdown,
        "ai_summary": bidder.risk_summary,
        "analyzed_at": bidder.risk_analyzed_at.isoformat() if bidder.risk_analyzed_at else None,
    }


@router.post("/api/bidders/{bidder_id}/risk/analyze")
def analyze_risk(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    result = analyze_bidder_risk(bidder_id, db=db, generate_ai_summary=True)
    if not result:
        raise HTTPException(status_code=500, detail="Risk analysis failed — check logs")

    log_action(
        db, action="risk_analyzed", entity_type="bidder", entity_id=str(bidder_id),
        user_id=str(current_user.id),
        details={"risk_score": result["risk_score"], "risk_level": result["risk_level"]},
    )
    return result


@router.get("/api/bidders/{bidder_id}/risk/timeline")
def get_risk_timeline(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    events = build_risk_timeline(bidder_id, db=db)
    return {"bidder_id": str(bidder_id), "events": events}


# ---------------------------------------------------------------------------
# Evidence chain endpoints
# ---------------------------------------------------------------------------

@router.get("/api/bidders/{bidder_id}/evidence")
def get_bidder_evidence(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the full evidence chain for all requirements for this bidder."""
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    compliance = db.query(ComplianceResult).filter(ComplianceResult.bidder_id == bidder_id).first()
    if not compliance:
        raise HTTPException(
            status_code=404,
            detail="No compliance evaluation found — run evaluation first",
        )

    try:
        req_results = json.loads(compliance.requirement_results or "[]")
    except (json.JSONDecodeError, TypeError):
        req_results = []

    verifications = (
        db.query(VerificationResult).filter(VerificationResult.bidder_id == bidder_id).all()
    )

    enriched = []
    for r in req_results:
        chain = _build_evidence_chain(r, verifications)
        vr_match = next(
            (v for v in verifications if str(v.requirement_id) == r.get("requirement_id")),
            None,
        )
        enriched.append({
            "requirement_id": r.get("requirement_id"),
            "requirement_title": r.get("requirement"),
            "category": r.get("category"),
            "mandatory": r.get("mandatory"),
            "status": r.get("status"),
            "reason_code": _reason_code(r),
            "required_value": str(r.get("required_value") or ""),
            "actual_value": str(r.get("actual_value") or ""),
            "confidence": None,
            "human_review_required": r.get("status") in ("NEEDS_REVIEW",),
            "evidence": {
                "document_name": r.get("source_document"),
                "snippet": r.get("evidence"),
                "page_number": None,
            },
            "verification": {
                "provider": vr_match.provider_name if vr_match else None,
                "status": vr_match.status.value if vr_match else None,
            } if vr_match else None,
            "evidence_chain": chain,
        })

    return {
        "bidder_id": str(bidder_id),
        "company_name": bidder.company_name,
        "tender_id": str(bidder.tender_id),
        "overall_status": compliance.overall_status.value if compliance.overall_status else None,
        "compliance_score": compliance.compliance_score,
        "requirement_results": enriched,
    }


@router.get("/api/requirements/{requirement_id}/evidence")
def get_requirement_evidence(
    requirement_id: str,
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns evidence for one specific requirement for a given bidder."""
    compliance = db.query(ComplianceResult).filter(ComplianceResult.bidder_id == bidder_id).first()
    if not compliance:
        raise HTTPException(status_code=404, detail="No compliance evaluation found")

    try:
        req_results = json.loads(compliance.requirement_results or "[]")
    except (json.JSONDecodeError, TypeError):
        req_results = []

    matched = next(
        (r for r in req_results if r.get("requirement_id") == requirement_id), None
    )
    if not matched:
        raise HTTPException(status_code=404, detail="Requirement result not found")

    verifications = (
        db.query(VerificationResult).filter(VerificationResult.bidder_id == bidder_id).all()
    )
    chain = _build_evidence_chain(matched, verifications)

    return {
        "requirement_id": requirement_id,
        "bidder_id": bidder_id,
        "status": matched.get("status"),
        "reason_code": _reason_code(matched),
        "evidence_chain": chain,
    }


# ---------------------------------------------------------------------------
# Final Decision endpoints
# ---------------------------------------------------------------------------

@router.post("/api/bidders/{bidder_id}/final-decision", response_model=FinalDecisionOut)
def submit_final_decision(
    bidder_id: str,
    payload: FinalDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.EVALUATOR)
    ),
):
    """
    Procurement officer submits the final qualification decision.
    If a decision already exists, a new versioned row is created and the
    previous one is marked superseded — original decision history is preserved.
    """
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    review_case = db.query(ReviewCase).filter(ReviewCase.bidder_id == bidder_id).first()
    if not review_case:
        raise HTTPException(
            status_code=400,
            detail="No review case exists for this bidder — create one first",
        )

    # Find the highest existing version
    existing_decisions = (
        db.query(FinalDecision)
        .filter(FinalDecision.bidder_id == bidder_id, FinalDecision.superseded == False)  # noqa
        .all()
    )
    new_version = (max((d.version for d in existing_decisions), default=0) + 1)

    # Mark old decisions superseded
    for old in existing_decisions:
        old.superseded = True
    db.flush()

    decision = FinalDecision(
        case_id=review_case.id,
        bidder_id=bidder_id,
        tender_id=bidder.tender_id,
        decision=FinalDecisionType(payload.decision),
        officer_id=current_user.id,
        officer_remarks=payload.officer_remarks,
        version=new_version,
        superseded=False,
        submitted_at=datetime.utcnow(),
    )
    db.add(decision)

    # Update review case status
    review_case.status = ReviewStatus.CLOSED
    review_case.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(decision)

    log_action(
        db,
        action="final_decision_submitted",
        entity_type="bidder",
        entity_id=str(bidder_id),
        user_id=str(current_user.id),
        details={
            "decision": payload.decision,
            "version": new_version,
            "remarks": payload.officer_remarks[:200],
        },
    )

    # Emit final decision alert
    from app.services.alert_service import emit_alert
    from app.models.alert import AlertEventType, AlertSeverity
    emit_alert(
        db=db,
        event_type=AlertEventType.FINAL_DECISION_SUBMITTED,
        title=f"Final Decision: {payload.decision.upper()}",
        description=f"Officer decision recorded for {bidder.company_name}: {payload.decision.upper()}",
        tender_id=str(bidder.tender_id),
        bidder_id=str(bidder_id),
        triggered_by=str(current_user.id),
    )

    return {
        "id": str(decision.id),
        "case_id": str(decision.case_id),
        "bidder_id": str(decision.bidder_id),
        "tender_id": str(decision.tender_id),
        "decision": decision.decision.value,
        "officer_id": str(decision.officer_id),
        "officer_remarks": decision.officer_remarks,
        "version": decision.version,
        "superseded": decision.superseded,
        "submitted_at": decision.submitted_at,
    }


@router.get("/api/bidders/{bidder_id}/final-decision")
def get_final_decision(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the current (latest non-superseded) final decision for a bidder."""
    decision = (
        db.query(FinalDecision)
        .filter(FinalDecision.bidder_id == bidder_id, FinalDecision.superseded == False)  # noqa
        .order_by(FinalDecision.version.desc())
        .first()
    )
    if not decision:
        raise HTTPException(status_code=404, detail="No final decision has been submitted yet")

    return {
        "id": str(decision.id),
        "case_id": str(decision.case_id),
        "bidder_id": str(decision.bidder_id),
        "tender_id": str(decision.tender_id),
        "decision": decision.decision.value,
        "officer_id": str(decision.officer_id),
        "officer_remarks": decision.officer_remarks,
        "version": decision.version,
        "superseded": decision.superseded,
        "submitted_at": decision.submitted_at,
    }


@router.get("/api/bidders/{bidder_id}/final-decision/history")
def get_decision_history(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """Returns all historical decision versions for a bidder (audit trail)."""
    decisions = (
        db.query(FinalDecision)
        .filter(FinalDecision.bidder_id == bidder_id)
        .order_by(FinalDecision.version.desc())
        .all()
    )
    return [
        {
            "id": str(d.id),
            "decision": d.decision.value,
            "officer_id": str(d.officer_id),
            "officer_remarks": d.officer_remarks,
            "version": d.version,
            "superseded": d.superseded,
            "submitted_at": d.submitted_at,
        }
        for d in decisions
    ]
