"""
Bidder document upload + AI extraction pipeline endpoints.

Mirrors the tenders.py upload/process/status pattern:
    POST /api/documents/upload           -> save file, create BidderDocument row
    POST /api/documents/{id}/process     -> kick off background extraction pipeline
    GET  /api/documents/{id}/status      -> poll pipeline progress
    GET  /api/documents/{id}             -> full document detail incl. extracted data
"""
import os

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.user import User, UserRole
from app.models.bidder import Bidder, BidderDocument, BidderDocumentType, DocumentProcessingStatus
from app.schemas.bidder import (
    BidderDocumentUploadOut,
    BidderDocumentStatusOut,
    BidderDocumentDetailOut,
)
from app.core.deps import require_roles, get_current_user
from app.core.file_validation import validate_document_bytes, safe_stored_filename
from app.core.logging_config import logger
from app.services.bidder_document_service import run_bidder_document_pipeline

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _coerce_document_type(raw_value: str) -> BidderDocumentType:
    try:
        return BidderDocumentType(raw_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid document_type '{raw_value}'. Must be one of: "
                + ", ".join(t.value for t in BidderDocumentType)
            ),
        )


@router.post("/upload", response_model=BidderDocumentUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    bidder_id: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    doc_type_enum = _coerce_document_type(document_type)

    contents = await file.read()
    file_kind = validate_document_bytes(file.filename, file.content_type, contents, settings.MAX_UPLOAD_SIZE_MB)

    bidder_dir = os.path.join(settings.UPLOAD_DIR, "bidders", str(bidder.id))
    os.makedirs(bidder_dir, exist_ok=True)

    stored_name = safe_stored_filename(file.filename)
    file_path = os.path.join(bidder_dir, stored_name)
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except OSError as e:
        logger.error(f"Failed to save uploaded document for bidder {bidder_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file") from e

    document = BidderDocument(
        bidder_id=bidder.id,
        document_type=doc_type_enum,
        file_path=file_path,
        original_filename=file.filename,
        file_kind=file_kind,
        processing_status=DocumentProcessingStatus.UPLOADED,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    logger.info(
        f"Bidder document uploaded: {bidder.company_name} / {file.filename} "
        f"(declared type={doc_type_enum.value}) by {current_user.email}"
    )

    return BidderDocumentUploadOut(
        message="File uploaded successfully. Call POST /{id}/process to start AI extraction.",
        filename=file.filename,
        document_id=document.id,
        processing_status=document.processing_status,
    )


@router.post("/{document_id}/process", response_model=BidderDocumentStatusOut)
def process_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    document = db.query(BidderDocument).filter(BidderDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.processing_status in (
        DocumentProcessingStatus.EXTRACTING_TEXT,
        DocumentProcessingStatus.EXTRACTING_DATA,
    ):
        raise HTTPException(status_code=409, detail="Document is already being processed")

    document.processing_status = DocumentProcessingStatus.EXTRACTING_TEXT
    document.processing_error = None
    db.commit()

    background_tasks.add_task(run_bidder_document_pipeline, str(document.id))
    logger.info(f"AI processing started for bidder document {document.id} by {current_user.email}")

    return BidderDocumentStatusOut(
        document_id=document.id,
        processing_status=document.processing_status,
        processing_error=document.processing_error,
        page_count=document.page_count,
        extraction_method=document.extraction_method,
    )


@router.get("/{document_id}/status", response_model=BidderDocumentStatusOut)
def get_document_status(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(BidderDocument).filter(BidderDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return BidderDocumentStatusOut(
        document_id=document.id,
        processing_status=document.processing_status,
        processing_error=document.processing_error,
        page_count=document.page_count,
        extraction_method=document.extraction_method,
    )


@router.get("/{document_id}", response_model=BidderDocumentDetailOut)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.api.routes.bidders import _serialize_document  # local import avoids circular top-level import

    document = db.query(BidderDocument).filter(BidderDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return _serialize_document(document)
