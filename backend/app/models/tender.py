import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, Enum, ForeignKey, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class TenderStatus(str, enum.Enum):
    """Business/lifecycle status of the tender itself."""
    DRAFT = "draft"
    OPEN = "open"
    UNDER_EVALUATION = "under_evaluation"
    CLOSED = "closed"


class ProcessingStatus(str, enum.Enum):
    """
    Status of the AI extraction PIPELINE for this tender's document.
    Distinct from TenderStatus (business lifecycle).
    """
    PENDING = "pending"                            # no document uploaded yet
    UPLOADED = "uploaded"                           # document uploaded, not yet processed
    EXTRACTING_TEXT = "extracting_text"             # PyMuPDF/OCR running
    TEXT_EXTRACTED = "text_extracted"                # text ready, AI extraction not started
    EXTRACTING_REQUIREMENTS = "extracting_requirements"  # AI service running
    COMPLETED = "completed"                          # requirements saved
    FAILED = "failed"                                 # see processing_error


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_ref_no = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    department = Column(String(255), nullable=True)  # requesting department/division
    description = Column(Text, nullable=True)
    organization = Column(String(255), default="Chennai Petroleum Corporation Limited (CPCL)")
    status = Column(Enum(TenderStatus), default=TenderStatus.DRAFT)
    tender_date = Column(DateTime, nullable=True)  # date tender was floated
    deadline = Column(DateTime, nullable=True)      # bid submission deadline

    # --- Document + extraction pipeline ---
    document_path = Column(String(1000), nullable=True)
    extracted_text = Column(Text, nullable=True)         # full text, page-marked
    extraction_method = Column(String(50), nullable=True)  # "pymupdf" | "ocr"
    page_count = Column(Integer, nullable=True)

    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    processing_error = Column(Text, nullable=True)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    requirements = relationship("TenderRequirement", back_populates="tender", cascade="all, delete-orphan")
    bidders = relationship("Bidder", back_populates="tender", cascade="all, delete-orphan")


class RequirementCategory(str, enum.Enum):
    IDENTITY = "identity"
    PAN = "pan"
    GST = "gst"
    UDYAM_MSME = "udyam_msme"
    COMPANY_REGISTRATION = "company_registration"
    FINANCIAL = "financial"
    TURNOVER = "turnover"
    INCOME_TAX = "income_tax"
    STARTUP_DPIIT = "startup_dpiit"
    NSIC = "nsic"
    EPFO = "epfo"
    ESIC = "esic"
    BLACKLIST_DEBARMENT = "blacklist_debarment"
    DIGILOCKER = "digilocker"
    BIS = "bis"
    MAKE_IN_INDIA = "make_in_india"
    OTHER = "other"


class VerificationType(str, enum.Enum):
    """How this requirement will eventually be checked against a bidder."""
    DOCUMENT = "document"           # requires a specific uploaded document
    THRESHOLD = "threshold"         # requires a numeric value to meet/exceed a threshold
    DECLARATION = "declaration"     # requires a signed self-declaration
    DATABASE_CHECK = "database_check"  # requires cross-check against an external DB (e.g. GeM blacklist)
    OTHER = "other"


class TenderRequirement(Base):
    __tablename__ = "tender_requirements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)

    category = Column(Enum(RequirementCategory), nullable=False, default=RequirementCategory.OTHER)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    clause_reference = Column(String(255), nullable=True)  # e.g. "Clause 4.2" if AI could identify it

    # --- Structured extraction fields ---
    minimum_value = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    period = Column(String(255), nullable=True)  # e.g. "last 3 financial years"

    mandatory = Column(Boolean, default=True, nullable=False)
    required_documents = Column(ARRAY(String), nullable=True)
    verification_type = Column(Enum(VerificationType), default=VerificationType.OTHER, nullable=False)

    # --- AI provenance / trust fields ---
    confidence = Column(Float, nullable=True)       # 0.0 - 1.0
    evidence = Column(Text, nullable=True)           # exact supporting text snippet
    page_number = Column(Integer, nullable=True)
    needs_review = Column(Boolean, default=False, nullable=False)  # low confidence / ambiguous
    extracted_by_ai = Column(Boolean, default=True, nullable=False)

    sequence_no = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    tender = relationship("Tender", back_populates="requirements")
