import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationChannel, NotificationStatus


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    bidder_id: uuid.UUID
    tender_id: Optional[uuid.UUID] = None
    channel: NotificationChannel
    status: NotificationStatus
    recipient: Optional[str] = None
    subject: Optional[str] = None
    message: str
    reason: Optional[str] = None
    created_at: datetime
