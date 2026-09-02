"""
Verification endpoints (Day 4).
Runs mock government-registry verification for a bidder and exposes results.
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.bidder import Bidder
from app.models.verification import VerificationResult
from app.schemas.verification import VerificationResultOut, VerificationRunSummaryOut
from app.core.deps import get_current_user, require_roles
from app.services.verification_service import verification_service

router = APIRouter(prefix="/api/verification", tags=["verification"])


def _serialize(vr: VerificationResult) -> dict:
    try:
        raw = json.loads(vr.raw_response) if vr.raw_response else {}
    except (json.JSONDecodeError, TypeError):
        raw = {}
    return {
        "id": vr.id,
        "bidder_id": vr.bidder_id,
        "requirement_id": vr.requirement_id,
        "bidder_document_id": vr.bidder_document_id,
        "status": vr.status,
        "provider_name": vr.provider_name,
        "identifier_checked": vr.identifier_checked,
        "raw_response": raw,
        "is_mock": vr.is_mock,
        "evidence_snippet": vr.evidence_snippet,
        "notes": vr.notes,
        "verified_at": vr.verified_at,
    }


@router.get("/bidder/{bidder_id}", response_model=List[VerificationResultOut])
def get_verification_results(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = db.query(VerificationResult).filter(VerificationResult.bidder_id == bidder_id).all()
    return [_serialize(r) for r in results]


@router.post("/bidder/{bidder_id}/run", response_model=VerificationRunSummaryOut)
def run_verification(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """
    Runs every mock external-registry check (GST/PAN/Udyam/company
    registration/BIS/blacklist) applicable to this bidder's tender and
    persists a VerificationResult row per requirement checked.
    """
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    try:
        summary = verification_service.verify_bidder_against_tender(
            bidder_id=bidder_id, db=db, user_id=str(current_user.id)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    results = db.query(VerificationResult).filter(VerificationResult.bidder_id == bidder_id).all()
    return {
        "bidder_id": bidder_id,
        "checks_run": len(summary),
        "results": [_serialize(r) for r in results],
    }
