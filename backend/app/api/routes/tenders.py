import os
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    BackgroundTasks,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.user import User, UserRole
from app.models.tender import Tender, TenderRequirement, ProcessingStatus
from app.models.verification import VerificationResult
from app.schemas.tender import (
    TenderCreate,
    TenderOut,
    TenderDetailOut,
    TenderRequirementOut,
    TenderStatusOut,
    TenderUploadOut,
)
from app.core.deps import require_roles, get_current_user
from app.core.file_validation import validate_pdf_bytes, safe_stored_filename
from app.core.logging_config import logger
from app.services.requirement_extraction_service import run_tender_processing_pipeline

router = APIRouter(prefix="/api/tenders", tags=["tenders"])


# ---------------------------------------------------------------------------
# Tender CRUD
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[TenderOut])
def list_tenders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Tender).order_by(Tender.created_at.desc()).all()


@router.post("/", response_model=TenderOut, status_code=status.HTTP_201_CREATED)
def create_tender(
    payload: TenderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    existing = db.query(Tender).filter(Tender.tender_ref_no == payload.tender_ref_no).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tender reference number already exists")

    tender = Tender(
        tender_ref_no=payload.tender_ref_no,
        title=payload.title,
        department=payload.department,
        description=payload.description,
        tender_date=payload.tender_date,
        deadline=payload.deadline,
        created_by=current_user.id,
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)
    logger.info(f"Tender created: {tender.tender_ref_no} by {current_user.email}")
    return tender


@router.get("/{tender_id}", response_model=TenderDetailOut)
def get_tender(
    tender_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


# ---------------------------------------------------------------------------
# Document upload + AI processing pipeline
# ---------------------------------------------------------------------------

@router.post("/{tender_id}/upload", response_model=TenderUploadOut)
async def upload_tender_document(
    tender_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    contents = await file.read()
    validate_pdf_bytes(file.filename, file.content_type, contents, settings.MAX_UPLOAD_SIZE_MB)

    tender_dir = os.path.join(settings.UPLOAD_DIR, "tenders", str(tender.id))
    os.makedirs(tender_dir, exist_ok=True)

    stored_name = safe_stored_filename(file.filename)
    file_path = os.path.join(tender_dir, stored_name)
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except OSError as e:
        logger.error(f"Failed to save uploaded file for tender {tender_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file") from e

    # A new document invalidates any previous extraction for this tender.
    tender.document_path = file_path
    tender.processing_status = ProcessingStatus.UPLOADED
    tender.processing_error = None
    tender.extracted_text = None
    tender.extraction_method = None
    tender.page_count = None
    # A re-upload invalidates old requirements — and any VerificationResult
    # rows that reference them, which must go first: VerificationResult has
    # no DB-level cascade on requirement_id, and bulk Query.delete() below
    # does not trigger ORM-level cascades, so deleting requirements first
    # would otherwise fail with a ForeignKeyViolation once any bidder has
    # been verified against this tender.
    old_requirement_ids = [
        r.id for r in db.query(TenderRequirement.id).filter(TenderRequirement.tender_id == tender.id)
    ]
    if old_requirement_ids:
        db.query(VerificationResult).filter(
            VerificationResult.requirement_id.in_(old_requirement_ids)
        ).delete(synchronize_session=False)
    db.query(TenderRequirement).filter(TenderRequirement.tender_id == tender.id).delete()
    db.commit()

    logger.info(
        f"Tender document uploaded: {tender.tender_ref_no} ({file.filename}) by {current_user.email}"
    )

    return TenderUploadOut(
        message="File uploaded successfully. Call POST /process to start AI extraction.",
        filename=file.filename,
        processing_status=tender.processing_status,
    )


@router.post("/{tender_id}/process", response_model=TenderStatusOut)
def process_tender(
    tender_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EVALUATOR)),
):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    if not tender.document_path:
        raise HTTPException(status_code=400, detail="Upload a tender document before processing")

    if tender.processing_status in (
        ProcessingStatus.EXTRACTING_TEXT,
        ProcessingStatus.EXTRACTING_REQUIREMENTS,
    ):
        raise HTTPException(status_code=409, detail="Tender is already being processed")

    tender.processing_status = ProcessingStatus.EXTRACTING_TEXT
    tender.processing_error = None
    db.commit()

    background_tasks.add_task(run_tender_processing_pipeline, str(tender.id))
    logger.info(f"AI processing started for tender {tender.tender_ref_no} by {current_user.email}")

    requirements_count = (
        db.query(TenderRequirement).filter(TenderRequirement.tender_id == tender.id).count()
    )
    return TenderStatusOut(
        processing_status=tender.processing_status,
        processing_error=tender.processing_error,
        requirements_count=requirements_count,
        page_count=tender.page_count,
        extraction_method=tender.extraction_method,
    )


@router.get("/{tender_id}/status", response_model=TenderStatusOut)
def get_tender_status(
    tender_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    requirements_count = (
        db.query(TenderRequirement).filter(TenderRequirement.tender_id == tender.id).count()
    )
    return TenderStatusOut(
        processing_status=tender.processing_status,
        processing_error=tender.processing_error,
        requirements_count=requirements_count,
        page_count=tender.page_count,
        extraction_method=tender.extraction_method,
    )


# ---------------------------------------------------------------------------
# Extracted requirements
# ---------------------------------------------------------------------------

@router.get("/{tender_id}/requirements", response_model=List[TenderRequirementOut])
def list_tender_requirements(
    tender_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    return (
        db.query(TenderRequirement)
        .filter(TenderRequirement.tender_id == tender_id)
        .order_by(TenderRequirement.sequence_no)
        .all()
    )


@router.get("/{tender_id}/requirements/{requirement_id}", response_model=TenderRequirementOut)
def get_tender_requirement(
    tender_id: str,
    requirement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    requirement = (
        db.query(TenderRequirement)
        .filter(
            TenderRequirement.tender_id == tender_id,
            TenderRequirement.id == requirement_id,
        )
        .first()
    )
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return requirement
