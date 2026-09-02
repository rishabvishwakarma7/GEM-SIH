"""Pydantic schemas for smart alerts."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AlertOut(BaseModel):
    id: str
    event_type: str
    severity: str
    title: str
    description: Optional[str] = None
    tender_id: Optional[str] = None
    bidder_id: Optional[str] = None
    requirement_id: Optional[str] = None
    document_id: Optional[str] = None
    action_required: bool
    read_at: Optional[datetime] = None
    dismissed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListOut(BaseModel):
    items: list[AlertOut]
    total: int
    unread_count: int
