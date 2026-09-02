import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=False)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    file_path = Column(String(1000), nullable=False)
    report_type = Column(String(100), default="compliance_summary")
    generated_at = Column(DateTime, default=datetime.utcnow)
