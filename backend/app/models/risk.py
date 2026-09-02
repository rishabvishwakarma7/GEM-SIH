"""
Risk intelligence models (Upgrade).

DocumentRiskAnalysis  - per-document suspicious signal analysis
DuplicateDocumentMatch - pairwise similarity/duplicate records
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey, Enum, Boolean, Float, Integer
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class DocumentRiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DuplicateMatchType(str, enum.Enum):
    EXACT = "exact"
    HIGH_SIMILARITY = "high_similarity"
    POSSIBLE_SIMILARITY = "possible_similarity"
    LOW_SIMILARITY = "low_similarity"


class DocumentRiskAnalysis(Base):
    """
    Per-document risk analysis result.  Upserted every time the document
    risk pipeline runs (one active row per bidder_document_id).

    risk_score is computed deterministically from individual signal weights
    in document_risk_service.py.  AI never sets this value.
    """
    __tablename__ = "document_risk_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bidder_document_id = Column(
        UUID(as_uuid=True), ForeignKey("bidder_documents.id"), nullable=False, unique=True
    )

    # --- Overall risk ---
    risk_score = Column(Float, default=0.0, nullable=False)   # 0–100, deterministic
    risk_level = Column(Enum(DocumentRiskLevel), default=DocumentRiskLevel.LOW, nullable=False)
    suspicious = Column(Boolean, default=False, nullable=False)

    # --- Signal breakdown (JSON list of {signal, weight, detail}) ---
    suspicion_signals = Column(Text, nullable=True)   # JSON array of signal dicts

    # --- Individual signal flags ---
    metadata_anomaly = Column(Boolean, default=False)
    date_inconsistency = Column(Boolean, default=False)
    identifier_mismatch = Column(Boolean, default=False)
    registry_mismatch = Column(Boolean, default=False)
    low_ai_confidence = Column(Boolean, default=False)
    type_mismatch_flag = Column(Boolean, default=False)

    # --- Raw metadata inspection ---
    pdf_creation_date = Column(String(100), nullable=True)
    pdf_modification_date = Column(String(100), nullable=True)
    pdf_producer = Column(String(255), nullable=True)
    pdf_author = Column(String(255), nullable=True)

    # --- AI narrative (optional, never changes risk_score) ---
    ai_risk_summary = Column(Text, nullable=True)

    analyzed_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("BidderDocument", back_populates="risk_analysis")


class DuplicateDocumentMatch(Base):
    """
    Pairwise duplicate / similarity record between two BidderDocuments.

    Always stored with source_document_id < target_document_id (UUID string
    comparison) to avoid symmetric duplicates.  Unique constraint enforces
    one row per pair.
    """
    __tablename__ = "duplicate_document_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_document_id = Column(
        UUID(as_uuid=True), ForeignKey("bidder_documents.id"), nullable=False
    )
    target_document_id = Column(
        UUID(as_uuid=True), ForeignKey("bidder_documents.id"), nullable=False
    )

    source_bidder_id = Column(UUID(as_uuid=True), ForeignKey("bidders.id"), nullable=False)
    target_bidder_id = Column(UUID(as_uuid=True), ForeignKey("bidders.id"), nullable=False)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)

    similarity_score = Column(Float, default=0.0)   # 0.0–1.0
    match_type = Column(Enum(DuplicateMatchType), nullable=False)

    # True when SHA-256 hashes match exactly
    exact_hash_match = Column(Boolean, default=False, nullable=False)

    reviewed = Column(Boolean, default=False, nullable=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

    detected_at = Column(DateTime, default=datetime.utcnow)
