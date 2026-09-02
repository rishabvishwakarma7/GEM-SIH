import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Float, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class ExtractedDocumentData(Base):
    """
    AI classification + structured-extraction output for one BidderDocument.
    One row per document (replaced on reprocess). The type-specific fields
    (pan, gstin, company_name, turnover_amount, ...) are stored as a single
    JSON blob in `structured_fields` since the field set genuinely varies by
    document type (PAN vs GST vs Financial Statement) — never invented,
    always null when the AI could not confidently read a value.
    """
    __tablename__ = "extracted_document_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bidder_document_id = Column(
        UUID(as_uuid=True), ForeignKey("bidder_documents.id"), nullable=False, unique=True
    )

    # --- AI document classification (may differ from the uploader's declared type) ---
    detected_document_type = Column(String(50), nullable=True)
    classification_confidence = Column(Float, nullable=True)
    type_mismatch = Column(Boolean, default=False, nullable=False)  # declared != detected

    # --- AI structured extraction ---
    structured_fields = Column(Text, nullable=True)        # JSON object, e.g. {"pan": "...", "company_name": "..."}
    missing_fields = Column(ARRAY(String), nullable=True)  # expected-but-not-found field names

    confidence = Column(Float, nullable=True)   # overall extraction confidence, 0.0-1.0
    evidence = Column(Text, nullable=True)       # exact supporting text snippet
    page_number = Column(Integer, nullable=True)
    is_readable = Column(Boolean, default=True, nullable=False)
    needs_review = Column(Boolean, default=False, nullable=False)

    extracted_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("BidderDocument", back_populates="extracted_data")
