"""
Compliance endpoints (Day 4).
Runs the deterministic rule engine for a bidder, and exposes results +
tender-wide bidder comparison.
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.bidder import Bidder
from app.models.compliance import ComplianceResult
from app.schemas.compliance import (
    ComplianceResultOut,
    ComplianceResultDetailOut,
    BidderComparisonOut,
)
from app.core.deps import get_current_user, require_roles
from app.services.compliance_engine import compliance_engine

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


def _serialize_detail(cr: ComplianceResult) -> dict:
    try:
        req_results = json.loads(cr.requirement_results) if cr.requirement_results else []
    except (json.JSONDecodeError, TypeError):
        req_results = []
    return {
        "id": cr.id,
        "tender_id": cr.tender_id,
        "bidder_id": cr.bidder_id,
        "overall_status": cr.overall_status,
        "risk_level": cr.risk_level,
        "compliance_score": cr.compliance_score,
        "mandatory_failed": cr.mandatory_failed,
        "explanation": cr.explanation,
        "ai_recommendation": cr.ai_recommendation,
        "total_requirements": cr.total_requirements,
        "compliant_count": cr.compliant_count,
        "non_compliant_count": cr.non_compliant_count,
        "needs_review_count": cr.needs_review_count,
        "evaluated_at": cr.evaluated_at,
        "requirement_results": req_results,
    }


@router.get("/tender/{tender_id}", response_model=List[ComplianceResultOut])
def get_compliance_results(
    tender_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ComplianceResult).filter(ComplianceResult.tender_id == tender_id).all()


@router.get("/tender/{tender_id}/comparison", response_model=BidderComparisonOut)
def get_bidder_comparison(
    tender_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        rows = compliance_engine.get_bidder_comparison(tender_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"tender_id": tender_id, "bidders": rows}


@router.get("/bidder/{bidder_id}", response_model=ComplianceResultDetailOut)
def get_bidder_compliance(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = db.query(ComplianceResult).filter(ComplianceResult.bidder_id == bidder_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="No compliance evaluation exists yet for this bidder")
    return _serialize_detail(result)


@router.post("/bidder/{bidder_id}/evaluate", response_model=ComplianceResultDetailOut)
def evaluate_bidder_compliance(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """
    Runs the deterministic rule engine for this bidder against their tender's
    requirements, using whatever bidder-extracted data and verification
    results currently exist (run POST /api/verification/bidder/{id}/run
    first for the registry-backed requirements to be anything other than
    NEEDS_REVIEW).
    """
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    try:
        outcome = compliance_engine.evaluate_bidder(
            tender_id=str(bidder.tender_id), bidder_id=bidder_id, db=db, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return _serialize_detail(outcome["compliance_result"])


@router.post("/tender/{tender_id}/batch-evaluate")
def batch_evaluate_tender(
    tender_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """
    Bulk/batch operation (Day 6): runs verification + the compliance rule
    engine for EVERY bidder registered under this tender in one call, instead
    of the evaluator opening each bidder one at a time. One bidder failing
    does not stop the rest of the batch - check `success`/`error` per row.
    """
    try:
        summaries = compliance_engine.evaluate_all_bidders(
            tender_id=tender_id, db=db, user_id=str(current_user.id), run_verification=True
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "tender_id": tender_id,
        "bidders_processed": len(summaries),
        "results": summaries,
    }
