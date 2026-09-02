"""
Multi-level human review workflow models (Upgrade).

ReviewCase   - one case per bidder per review cycle
ReviewAction - immutable log of every action taken on a case
FinalDecision - procurement officer's final qualification decision
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ReviewLevel(str, enum.Enum):
    EVALUATOR = "evaluator"
    SENIOR_EVALUATOR = "senior_evaluator"
    PROCUREMENT_OFFICER = "procurement_officer"


class ReviewStatus(str, enum.Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_REVIEW = "in_review"
    ESCALATED = "escalated"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLARIFICATION_REQUIRED = "clarification_required"
    CLOSED = "closed"


class ReviewPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewActionType(str, enum.Enum):
    ASSIGNED = "assigned"
    EVIDENCE_APPROVED = "evidence_approved"
    EVIDENCE_REJECTED = "evidence_rejected"
    CLARIFICATION_REQUESTED = "clarification_requested"
    ESCALATED = "escalated"
    NOTE_ADDED = "note_added"
    SUSPICIOUS_DOCUMENT_REVIEWED = "suspicious_document_reviewed"
    IDENTITY_VARIATION_ACCEPTED = "identity_variation_accepted"
    IDENTITY_VARIATION_REJECTED = "identity_variation_rejected"
    STATUS_CHANGED = "status_changed"
    RESOLVED = "resolved"


class FinalDecisionType(str, enum.Enum):
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    CLARIFICATION_REQUIRED = "clarification_required"


class ReviewCase(Base):
    __tablename__ = "review_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)
    bidder_id = Column(UUID(as_uuid=True), ForeignKey("bidders.id"), nullable=False, unique=True)

    # Current state
    status = Column(Enum(ReviewStatus), default=ReviewStatus.OPEN, nullable=False)
    priority = Column(Enum(ReviewPriority), default=ReviewPriority.MEDIUM, nullable=False)
    review_level = Column(Enum(ReviewLevel), default=ReviewLevel.EVALUATOR, nullable=False)

    # Why was this case created?
    reason = Column(Text, nullable=True)       # human-readable summary
    trigger_events = Column(Text, nullable=True)  # JSON list of AlertEventType strings

    # Assignment
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)

    # Lifecycle timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    actions = relationship(
        "ReviewAction", back_populates="case",
        order_by="ReviewAction.created_at",
        cascade="all, delete-orphan",
    )
    final_decision = relationship(
        "FinalDecision", back_populates="case",
        uselist=False, cascade="all, delete-orphan",
    )


class ReviewAction(Base):
    """
    Immutable action log entry.  Never updated — new row for each action.
    """
    __tablename__ = "review_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("review_cases.id"), nullable=False)

    action_type = Column(Enum(ReviewActionType), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    actor_role = Column(String(50), nullable=True)

    notes = Column(Text, nullable=True)
    # JSON blob: before/after status, document_id referenced, etc.
    details = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("ReviewCase", back_populates="actions")


class FinalDecision(Base):
    """
    Procurement officer's final qualification decision.
    Edits are NOT silently overwritten — a new version row is created each time
    (version column).  The active decision is the one with the highest version.
    """
    __tablename__ = "final_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("review_cases.id"), nullable=False)
    bidder_id = Column(UUID(as_uuid=True), ForeignKey("bidders.id"), nullable=False)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)

    decision = Column(Enum(FinalDecisionType), nullable=False)
    officer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    officer_remarks = Column(Text, nullable=False)

    version = Column(Integer, default=1, nullable=False)
    superseded = Column(Boolean, default=False, nullable=False)  # True for old versions

    submitted_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("ReviewCase", back_populates="final_decision")
