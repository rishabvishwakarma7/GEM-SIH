import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class VerificationStatus(str, enum.Enum):
    VERIFIED = "verified"       # provider confirmed the value / clean record
    MISMATCH = "mismatch"       # provider returned a record but it fails the required condition
    NOT_FOUND = "not_found"     # identifier not found in the (mock) registry
    PENDING = "pending"         # not yet run


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bidder_id = Column(UUID(as_uuid=True), ForeignKey("bidders.id"), nullable=False)
    requirement_id = Column(UUID(as_uuid=True), ForeignKey("tender_requirements.id"), nullable=False)
    bidder_document_id = Column(UUID(as_uuid=True), ForeignKey("bidder_documents.id"), nullable=True)

    status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING)

    # --- Day 4: mock external verification provider metadata ---
    provider_name = Column(String(100), nullable=True)   # e.g. "gst_mock", "pan_mock", "blacklist_mock"
    identifier_checked = Column(String(255), nullable=True)  # the GSTIN/PAN/CIN/etc. that was looked up
    raw_response = Column(Text, nullable=True)            # JSON blob: the provider's mock response payload
    is_mock = Column(Boolean, default=True, nullable=False)  # always True until a real API is wired in

    evidence_snippet = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    verified_at = Column(DateTime, default=datetime.utcnow)
