"""
Smart Alert model (Upgrade).

Persists every generated alert regardless of delivery status.
Alerts are event-driven and reference the entity that triggered them.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertEventType(str, enum.Enum):
    COMPLIANCE_NON_COMPLIANT = "compliance_non_compliant"
    MANDATORY_REQUIREMENT_FAILED = "mandatory_requirement_failed"
    HIGH_RISK_BIDDER = "high_risk_bidder"
    SUSPICIOUS_DOCUMENT = "suspicious_document"
    DUPLICATE_DOCUMENT = "duplicate_document"
    REGISTRY_MISMATCH = "registry_mismatch"
    IDENTITY_INCONSISTENCY = "identity_inconsistency"
    DOCUMENT_MISSING = "document_missing"
    DOCUMENT_EXPIRED = "document_expired"
    LOW_AI_CONFIDENCE = "low_ai_confidence"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    REVIEW_ESCALATED = "review_escalated"
    FINAL_DECISION_SUBMITTED = "final_decision_submitted"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # --- Classification ---
    event_type = Column(Enum(AlertEventType), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False, default=AlertSeverity.MEDIUM)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # --- Entity references (all nullable; only relevant ones set) ---
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=True)
    bidder_id = Column(UUID(as_uuid=True), ForeignKey("bidders.id"), nullable=True)
    requirement_id = Column(UUID(as_uuid=True), ForeignKey("tender_requirements.id"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("bidder_documents.id"), nullable=True)

    # --- Audience / delivery ---
    # target_user_id = None → alert is global (visible to all evaluators/officers)
    target_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action_required = Column(Boolean, default=False, nullable=False)

    # --- State ---
    read_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    # dismissed = permanently hidden; still kept for audit
    dismissed = Column(Boolean, default=False, nullable=False)

    triggered_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
