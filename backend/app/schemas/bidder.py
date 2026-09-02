import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.bidder import (
    BidderDocumentType,
    DocumentProcessingStatus,
    BidderConsistencyStatus,
)


# ---------- Extracted document data ----------

class ExtractedDocumentDataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    detected_document_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    type_mismatch: bool

    structured_fields: Optional[Dict[str, Any]] = None
    missing_fields: Optional[List[str]] = None

    confidence: Optional[float] = None
    evidence: Optional[str] = None
    page_number: Optional[int] = None
    is_readable: bool
    needs_review: bool

    extracted_at: datetime


# ---------- Bidder documents ----------

class BidderDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bidder_id: uuid.UUID
    document_type: BidderDocumentType
    original_filename: str
    file_kind: str
    uploaded_at: datetime

    extraction_method: Optional[str] = None
    page_count: Optional[int] = None
    processing_status: DocumentProcessingStatus
    processing_error: Optional[str] = None


class BidderDocumentDetailOut(BidderDocumentOut):
    extracted_data: Optional[ExtractedDocumentDataOut] = None


class BidderDocumentUploadOut(BaseModel):
    message: str
    filename: str
    document_id: uuid.UUID
    processing_status: DocumentProcessingStatus


class BidderDocumentStatusOut(BaseModel):
    document_id: uuid.UUID
    processing_status: DocumentProcessingStatus
    processing_error: Optional[str] = None
    page_count: Optional[int] = None
    extraction_method: Optional[str] = None


# ---------- Bidder consistency report ----------

class IdentityWarning(BaseModel):
    field: str                      # "company_name" | "pan" | "gstin"
    message: str
    documents: List[str]            # document_type values involved


class BidderConsistencyReportOut(BaseModel):
    missing_documents: List[str] = []
    identity_warnings: List[IdentityWarning] = []
    documents_analyzed: int = 0
    documents_failed: int = 0
    documents_needing_review: int = 0


# ---------- Bidders ----------

class BidderBase(BaseModel):
    company_name: str
    gem_seller_id: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None


class BidderCreate(BidderBase):
    tender_id: uuid.UUID


class BidderOut(BidderBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tender_id: uuid.UUID
    consistency_status: BidderConsistencyStatus
    missing_document_types: Optional[List[str]] = None
    analyzed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class BidderDetailOut(BidderOut):
    documents: List[BidderDocumentDetailOut] = []
    consistency_report: Optional[BidderConsistencyReportOut] = None
