import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, ConfigDict

from app.models.verification import VerificationStatus


class VerificationResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    bidder_id: uuid.UUID
    requirement_id: uuid.UUID
    bidder_document_id: Optional[uuid.UUID] = None
    status: VerificationStatus
    provider_name: Optional[str] = None
    identifier_checked: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    is_mock: bool
    evidence_snippet: Optional[str] = None
    notes: Optional[str] = None
    verified_at: datetime


class VerificationRunSummaryOut(BaseModel):
    bidder_id: str
    checks_run: int
    results: List[VerificationResultOut]
