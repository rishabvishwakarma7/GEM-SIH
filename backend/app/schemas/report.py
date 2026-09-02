import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tender_id: uuid.UUID
    file_path: str
    report_type: str
    generated_at: datetime
