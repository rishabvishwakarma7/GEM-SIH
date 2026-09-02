import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, Enum, ForeignKey, Integer, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class BidderDocumentType(str, enum.Enum):
    """
    Supported bidder document categories. Deliberately aligned with
    TenderRequirement.category (app.models.tender) so a tender requirement's
    category can be matched against an uploaded bidder document's type for
    missing-document detection.
    """
    PAN = "pan"
    GST = "gst"
    UDYAM_MSME = "udyam_msme"
    COMPANY_REGISTRATION = "company_registration"
    INCOME_TAX = "income_tax"
    STARTUP_DPIIT = "startup_dpiit"
    NSIC = "nsic"
    EPFO = "epfo"
    ESIC = "esic"
    DIGILOCKER = "digilocker"
    BIS = "bis"
    FINANCIAL_STATEMENT = "financial_statement"
    TURNOVER_CERTIFICATE = "turnover_certificate"
    MAKE_IN_INDIA = "make_in_india"
    OTHER = "other"


class DocumentProcessingStatus(str, enum.Enum):
    """Status of the per-document AI extraction pipeline (distinct per BidderDocument)."""
    UPLOADED = "uploaded"                 # file saved, not yet processed
    EXTRACTING_TEXT = "extracting_text"   # PyMuPDF/OCR/image-OCR running
    TEXT_EXTRACTED = "text_extracted"     # text ready, AI extraction not started
    EXTRACTING_DATA = "extracting_data"   # AI classification + structured extraction running
    COMPLETED = "completed"               # structured data saved
    FAILED = "failed"                     # see processing_error


class BidderConsistencyStatus(str, enum.Enum):
    """Bidder-level rollup status from the consistency/missing-document check."""
    NOT_ANALYZED = "not_analyzed"
    CONSISTENT = "consistent"
    NEEDS_REVIEW = "needs_review"
    INCONSISTENT = "inconsistent"


class Bidder(Base):
    __tablename__ = "bidders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)
    company_name = Column(String(500), nullable=False)
    gem_seller_id = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)

    # --- Bidder-level consistency / missing-document analysis ---
    # Recomputed automatically whenever a document finishes processing, and
    # on demand via POST /api/bidders/{id}/analyze.
    consistency_status = Column(
        Enum(BidderConsistencyStatus), default=BidderConsistencyStatus.NOT_ANALYZED, nullable=False
    )
    consistency_report = Column(Text, nullable=True)  # JSON-serialized BidderConsistencyReport
    missing_document_types = Column(ARRAY(String), nullable=True)
    analyzed_at = Column(DateTime, nullable=True)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- Upgrade: Risk Intelligence ---
    risk_score = Column(Float, nullable=True)           # 0–100, deterministic
    risk_level = Column(String(20), nullable=True)       # low/medium/high/critical
    risk_factors = Column(Text, nullable=True)           # JSON list of risk factor dicts
    risk_summary = Column(Text, nullable=True)           # AI narrative (never changes score)
    risk_analyzed_at = Column(DateTime, nullable=True)

    tender = relationship("Tender", back_populates="bidders")
    documents = relationship(
        "BidderDocument", back_populates="bidder", cascade="all, delete-orphan",
        order_by="BidderDocument.uploaded_at",
    )


class BidderDocument(Base):
    __tablename__ = "bidder_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bidder_id = Column(UUID(as_uuid=True), ForeignKey("bidders.id"), nullable=False)

    # Type the uploader declared at upload time (dropdown selection).
    document_type = Column(Enum(BidderDocumentType), nullable=False, default=BidderDocumentType.OTHER)

    file_path = Column(String(1000), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_kind = Column(String(10), nullable=False, default="pdf")  # "pdf" | "image"
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # --- Extraction pipeline (mirrors Tender's pipeline fields) ---
    extracted_text = Column(Text, nullable=True)
    extraction_method = Column(String(50), nullable=True)  # "pymupdf" | "ocr" | "image_ocr"
    page_count = Column(Integer, nullable=True)

    processing_status = Column(
        Enum(DocumentProcessingStatus), default=DocumentProcessingStatus.UPLOADED, nullable=False
    )
    processing_error = Column(Text, nullable=True)

    # --- Upgrade: duplicate detection + risk ---
    file_hash = Column(String(64), nullable=True, index=True)   # SHA-256 hex digest
    document_fingerprint = Column(Text, nullable=True)          # normalized text fingerprint

    bidder = relationship("Bidder", back_populates="documents")
    extracted_data = relationship(
        "ExtractedDocumentData", back_populates="document",
        uselist=False, cascade="all, delete-orphan",
    )
    # Upgrade: risk analysis (one row per document)
    risk_analysis = relationship(
        "DocumentRiskAnalysis", back_populates="document",
        uselist=False, cascade="all, delete-orphan",
    )
