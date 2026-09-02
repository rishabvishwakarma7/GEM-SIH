"""
Notification model (Day 6) - a persisted record of every alert the platform
attempted to send a bidder about non-compliance / missing documents, whether
or not the underlying email/SMS actually went out (see notification_service).
Keeping a row even for skipped/failed sends means the evaluator can always see
"was this bidder told?" from the UI without checking server logs.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"


class NotificationStatus(str, enum.Enum):
    SENT = "sent"            # handed off to the provider successfully
    FAILED = "failed"        # provider raised an error
    SKIPPED = "skipped"      # channel not configured/enabled - recorded, not sent


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bidder_id = Column(UUID(as_uuid=True), ForeignKey("bidders.id"), nullable=False)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=True)

    channel = Column(Enum(NotificationChannel), nullable=False)
    status = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.SKIPPED)

    recipient = Column(String(255), nullable=True)   # email address or phone number
    subject = Column(String(500), nullable=True)
    message = Column(Text, nullable=False)
    reason = Column(String(255), nullable=True)       # why it was skipped/failed, if applicable

    triggered_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
