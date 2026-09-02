"""
Report generation endpoints (Day 5).
Generates a real PDF (ReportLab) and CSV export of a bidder's compliance
report on demand, streams the file back, and persists a Report row + audit
log entry for traceability. Files are also written to disk under
UPLOAD_DIR/reports so they can be re-downloaded without regenerating.
"""
import os
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.models.bidder import Bidder
from app.models.report import Report
from app.schemas.report import ReportOut
from app.core.deps import get_current_user, require_roles
from app.services.report_generator import report_generator
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/reports", tags=["reports"])

REPORTS_DIR = os.path.join(settings.UPLOAD_DIR, "reports")


def _reports_dir() -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    return REPORTS_DIR


@router.get("/tender/{tender_id}", response_model=List[ReportOut])
def get_reports(
    tender_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Report)
        .filter(Report.tender_id == tender_id)
        .order_by(Report.generated_at.desc())
        .all()
    )


@router.get("/bidder/{bidder_id}/pdf")
def generate_bidder_report_pdf(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates (or regenerates) the compliance report PDF for a bidder and streams it back."""
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    try:
        pdf_bytes = report_generator.generate_compliance_report_pdf(bidder_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    filename = f"compliance_report_{bidder.company_name.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    filepath = os.path.join(_reports_dir(), filename)
    with open(filepath, "wb") as f:
        f.write(pdf_bytes)

    report_row = Report(
        tender_id=bidder.tender_id,
        generated_by=current_user.id,
        file_path=filepath,
        report_type="compliance_summary_pdf",
    )
    db.add(report_row)
    db.commit()

    log_action(
        db, action="report_generated", entity_type="bidder", entity_id=str(bidder_id),
        user_id=str(current_user.id), details={"format": "pdf", "filename": filename},
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/bidder/{bidder_id}/csv")
def generate_bidder_report_csv(
    bidder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates a CSV export of a bidder's requirement-wise compliance results."""
    bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    try:
        csv_bytes = report_generator.generate_compliance_report_csv(bidder_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    filename = f"compliance_report_{bidder.company_name.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
    filepath = os.path.join(_reports_dir(), filename)
    with open(filepath, "wb") as f:
        f.write(csv_bytes)

    report_row = Report(
        tender_id=bidder.tender_id,
        generated_by=current_user.id,
        file_path=filepath,
        report_type="compliance_summary_csv",
    )
    db.add(report_row)
    db.commit()

    log_action(
        db, action="report_generated", entity_type="bidder", entity_id=str(bidder_id),
        user_id=str(current_user.id), details={"format": "csv", "filename": filename},
    )

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/download/{report_id}")
def download_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-downloads a previously generated report by its Report row id."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    media_type = "application/pdf" if report.file_path.endswith(".pdf") else "text/csv"
    return FileResponse(report.file_path, media_type=media_type, filename=os.path.basename(report.file_path))
