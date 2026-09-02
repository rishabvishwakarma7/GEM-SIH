import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict

from app.models.tender import TenderStatus, ProcessingStatus, RequirementCategory, VerificationType


# ---------- Tender Requirements ----------

class TenderRequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tender_id: uuid.UUID
    category: RequirementCategory
    title: str
    description: str
    clause_reference: Optional[str] = None

    minimum_value: Optional[float] = None
    currency: Optional[str] = None
    period: Optional[str] = None

    mandatory: bool
    required_documents: Optional[List[str]] = None
    verification_type: VerificationType

    confidence: Optional[float] = None
    evidence: Optional[str] = None
    page_number: Optional[int] = None
    needs_review: bool
    extracted_by_ai: bool

    sequence_no: int
    created_at: datetime


# ---------- Tenders ----------

class TenderBase(BaseModel):
    tender_ref_no: str
    title: str
    department: Optional[str] = None
    description: Optional[str] = None
    tender_date: Optional[datetime] = None
    deadline: Optional[datetime] = None


class TenderCreate(TenderBase):
    pass


class TenderOut(TenderBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization: str
    status: TenderStatus

    document_path: Optional[str] = None
    extraction_method: Optional[str] = None
    page_count: Optional[int] = None

    processing_status: ProcessingStatus
    processing_error: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class TenderDetailOut(TenderOut):
    requirements: List[TenderRequirementOut] = []


class TenderStatusOut(BaseModel):
    processing_status: ProcessingStatus
    processing_error: Optional[str] = None
    requirements_count: int
    page_count: Optional[int] = None
    extraction_method: Optional[str] = None


class TenderUploadOut(BaseModel):
    message: str
    filename: str
    processing_status: ProcessingStatus
