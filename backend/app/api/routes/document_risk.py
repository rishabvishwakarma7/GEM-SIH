"""
Document risk + duplicate detection API routes (Upgrade — Task 8).

GET  /api/documents/{id}/risk            — get existing risk analysis
POST /api/documents/{id}/risk/analyze    — trigger/re-run risk analysis
GET  /api/documents/duplicates           — list all duplicate matches (tender-scoped)
POST /api/documents/{id}/duplicate-check — run duplicate check for one document
POST /api/documents/duplicates/{match_id}/review — mark a match reviewed
"""
import json
import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.bidder import BidderDocument
from app.models.risk import DocumentRiskAnalysis, DuplicateDocumentMatch
from app.schemas.risk import DocumentRiskOut, DuplicateMatchOut, DuplicateReviewRequest
from app.core.deps import get_current_user, require_roles
from app.services.document_risk_service import analyze_document_risk
from app.services.duplicate_detection_service import (
    run_duplicate_check_for_document,
    run_duplicate_check_for_tender,
)
from app.core.logging_config import logger

router = APIRouter(prefix="/api/documents", tags=["document-risk"])


def _serialize_risk(record: DocumentRiskAnalysis) -> dict:
    try:
        signals = json.loads(record.suspicion_signals or "[]")
    except (json.JSONDecodeError, TypeError):
        signals = []
    return {
        "id": str(record.id),
        "bidder_document_id": str(record.bidder_document_id),
        "risk_score": record.risk_score,
        "risk_level": record.risk_level.value if hasattr(record.risk_level, "value") else str(record.risk_level),
        "suspicious": record.suspicious,
        "suspicion_signals": signals,
        "metadata_anomaly": record.metadata_anomaly,
        "date_inconsistency": record.date_inconsistency,
        "identifier_mismatch": record.identifier_mismatch,
        "registry_mismatch": record.registry_mismatch,
        "low_ai_confidence": record.low_ai_confidence,
        "type_mismatch_flag": record.type_mismatch_flag,
        "pdf_creation_date": record.pdf_creation_date,
        "pdf_modification_date": record.pdf_modification_date,
        "pdf_producer": record.pdf_producer,
        "pdf_author": record.pdf_author,
        "ai_risk_summary": record.ai_risk_summary,
        "analyzed_at": record.analyzed_at,
    }


def _serialize_match(m: DuplicateDocumentMatch) -> dict:
    return {
        "id": str(m.id),
        "source_document_id": str(m.source_document_id),
        "target_document_id": str(m.target_document_id),
        "source_bidder_id": str(m.source_bidder_id),
        "target_bidder_id": str(m.target_bidder_id),
        "tender_id": str(m.tender_id),
        "similarity_score": round(m.similarity_score * 100, 1),
        "match_type": m.match_type.value if hasattr(m.match_type, "value") else str(m.match_type),
        "exact_hash_match": m.exact_hash_match,
        "reviewed": m.reviewed,
        "reviewed_by": str(m.reviewed_by) if m.reviewed_by else None,
        "reviewed_at": m.reviewed_at,
        "review_notes": m.review_notes,
        "detected_at": m.detected_at,
    }


# ---------------------------------------------------------------------------
# Risk analysis endpoints
# ---------------------------------------------------------------------------

@router.get("/{document_id}/risk", response_model=DocumentRiskOut)
def get_document_risk(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the latest risk analysis for a bidder document."""
    doc = db.query(BidderDocument).filter(BidderDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    record = (
        db.query(DocumentRiskAnalysis)
        .filter(DocumentRiskAnalysis.bidder_document_id == document_id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=404,
            detail="No risk analysis exists yet — call POST /risk/analyze first",
        )
    return _serialize_risk(record)


@router.post("/{document_id}/risk/analyze", response_model=DocumentRiskOut)
def analyze_risk(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """Triggers (or re-runs) document risk analysis and returns the result."""
    doc = db.query(BidderDocument).filter(BidderDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    result = analyze_document_risk(document_id, db=db)
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Risk analysis could not be run — document may not be fully processed yet",
        )
    return _serialize_risk(result)


# ---------------------------------------------------------------------------
# Duplicate detection endpoints
# ---------------------------------------------------------------------------

@router.get("/duplicates", response_model=List[DuplicateMatchOut])
def list_duplicate_matches(
    tender_id: Optional[str] = Query(None),
    bidder_id: Optional[str] = Query(None),
    match_type: Optional[str] = Query(None),
    reviewed: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists duplicate/similar document matches, with optional filters."""
    q = db.query(DuplicateDocumentMatch)
    if tender_id:
        q = q.filter(DuplicateDocumentMatch.tender_id == tender_id)
    if bidder_id:
        q = q.filter(
            (DuplicateDocumentMatch.source_bidder_id == bidder_id)
            | (DuplicateDocumentMatch.target_bidder_id == bidder_id)
        )
    if match_type:
        q = q.filter(DuplicateDocumentMatch.match_type == match_type)
    if reviewed is not None:
        q = q.filter(DuplicateDocumentMatch.reviewed == reviewed)

    q = q.order_by(DuplicateDocumentMatch.similarity_score.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return [_serialize_match(m) for m in rows]


@router.post("/{document_id}/duplicate-check")
def run_duplicate_check(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """Runs duplicate detection for a specific document against all other docs in its tender."""
    doc = db.query(BidderDocument).filter(BidderDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    matches = run_duplicate_check_for_document(document_id, db=db)
    return {
        "document_id": document_id,
        "matches_found": len(matches),
        "matches": matches,
    }


@router.post("/duplicates/{match_id}/review")
def review_duplicate_match(
    match_id: str,
    payload: DuplicateReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """Marks a duplicate match as reviewed with optional notes."""
    from datetime import datetime
    match = db.query(DuplicateDocumentMatch).filter(DuplicateDocumentMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Duplicate match not found")

    match.reviewed = payload.reviewed
    match.reviewed_by = current_user.id
    match.reviewed_at = datetime.utcnow()
    match.review_notes = payload.review_notes
    db.commit()
    db.refresh(match)
    return _serialize_match(match)
