import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.tender import Tender
from app.models.bidder import Bidder, BidderDocument
from app.models.document import ExtractedDocumentData
from app.schemas.bidder import (
    BidderCreate,
    BidderOut,
    BidderDetailOut,
    BidderDocumentDetailOut,
    ExtractedDocumentDataOut,
    BidderConsistencyReportOut,
)
from app.core.deps import require_roles, get_current_user
from app.core.logging_config import logger
from app.services.bidder_consistency_service import analyze_bidder

router = APIRouter(prefix="/api/bidders", tags=["bidders"])


def _serialize_extracted_data(extracted: Optional[ExtractedDocumentData]) -> Optional[dict]:
    if not extracted:
        return None
    try:
        fields = json.loads(extracted.structured_fields) if extracted.structured_fields else {}
    except (json.JSONDecodeError, TypeError):
        fields = {}
    return {
        "detected_document_type": extracted.detected_document_type,
        "classification_confidence": extracted.classification_confidence,
        "type_mismatch": extracted.type_mismatch,
        "structured_fields": fields,
        "missing_fields": extracted.missing_fields or [],
        "confidence": extracted.confidence,
        "evidence": extracted.evidence,
        "page_number": extracted.page_number,
        "is_readable": extracted.is_readable,
        "needs_review": extracted.needs_review,
        "extracted_at": extracted.extracted_at,
    }


def _serialize_document(doc: BidderDocument) -> dict:
    return {
        "id": doc.id,
        "bidder_id": doc.bidder_id,
        "document_type": doc.document_type,
        "original_filename": doc.original_filename,
        "file_kind": doc.file_kind,
        "uploaded_at": doc.uploaded_at,
        "extraction_method": doc.extraction_method,
        "page_count": doc.page_count,
        "processing_status": doc.processing_status,
        "processing_error": doc.processing_error,
        "extracted_data": _serialize_extracted_data(doc.extracted_data),
    }


def _serialize_bidder_detail(bidder: Bidder) -> dict:
    try:
        report = json.loads(bidder.consistency_report) if bidder.consistency_report else None
    except (json.JSONDecodeError, TypeError):
        report = None
    return {
        "id": bidder.id,
        "tender_id": bidder.tender_id,
        "company_name": bidder.company_name,
        "gem_seller_id": bidder.gem_seller_id,
        "contact_email": bidder.contact_email,
        "contact_phone": bidder.contact_phone,
        "consistency_status": bidder.consistency_status,
        "missing_document_types": bidder.missing_document_types or [],
        "analyzed_at": bidder.analyzed_at,
        "created_at": bidder.created_at,
        "updated_at": bidder.updated_at,
        "documents": [_serialize_document(d) for d in bidder.documents],
        "consistency_report": report,
    }


# ---------------------------------------------------------------------------
# Bidder CRUD
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[BidderOut])
def list_bidders(
    tender_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Bidder)
    if tender_id:
        query = query.filter(Bidder.tender_id == tender_id)
    return query.order_by(Bidder.created_at.desc()).all()


@router.post("/", response_model=BidderOut, status_code=status.HTTP_201_CREATED)
def create_bidder(
    payload: BidderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    tender = db.query(Tender).filter(Tender.id == payload.tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    bidder = Bidder(
        tender_id=payload.tender_id,
        company_name=payload.company_name,
        gem_seller_id=payload.gem_seller_id,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        created_by=current_user.id,
    )
    db.add(bidder)
    db.commit()
    db.refresh(bidder)
    logger.info(f"Bidder created: {bidder.company_name} for tender {tender.tender_ref_no} by {current_user.email}")
    return bidder


@router.get("/{bidder_id}", response_model=BidderDetailOut)
def get_bidder(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")
    return _serialize_bidder_detail(bidder)


@router.post("/{bidder_id}/analyze", response_model=BidderConsistencyReportOut)
def analyze_bidder_now(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    """
    Manually re-runs missing-document detection + identity consistency
    checking for this bidder (also runs automatically after every document
    finishes processing).
    """
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    analyze_bidder(bidder_id, db=db)
    db.refresh(bidder)

    try:
        report = json.loads(bidder.consistency_report) if bidder.consistency_report else {}
    except (json.JSONDecodeError, TypeError):
        report = {}
    return report


@router.get("/{bidder_id}/documents", response_model=List[BidderDocumentDetailOut])
def list_bidder_documents(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")
    return [_serialize_document(d) for d in bidder.documents]
