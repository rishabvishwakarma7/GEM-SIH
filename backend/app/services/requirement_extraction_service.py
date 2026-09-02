"""
Requirement extraction service — orchestrates the full Tender Intelligence
pipeline for a single tender:

    document (PDF) -> document_processor -> raw text
                    -> ai_service          -> structured requirement candidates
                    -> validated + persisted as TenderRequirement rows

Runs as a FastAPI BackgroundTask, so it opens its own DB session (the
request-scoped session from the route handler is already closed by the
time this runs).

Every stage updates Tender.processing_status so the frontend can poll
GET /api/tenders/{id}/status and show live progress. Any exception at any
stage is caught, logged, and recorded on Tender.processing_error rather
than crashing the background task silently.
"""
from app.database import SessionLocal
from app.models.tender import (
    Tender,
    TenderRequirement,
    ProcessingStatus,
    RequirementCategory,
    VerificationType,
)
from app.services.document_processor import document_processor, DocumentProcessingError
from app.services.ai_service import ai_service, AIExtractionError
from app.core.logging_config import logger

# Requirements below this AI confidence are auto-flagged for manual review,
# regardless of what the AI otherwise concluded.
CONFIDENCE_REVIEW_THRESHOLD = 0.6

MIN_EXTRACTED_TEXT_CHARS = 20


def _coerce_category(raw_value) -> RequirementCategory:
    if not raw_value:
        return RequirementCategory.OTHER
    normalized = str(raw_value).strip().lower().replace(" ", "_").replace("-", "_")
    try:
        return RequirementCategory(normalized)
    except ValueError:
        logger.warning(f"Unrecognized requirement category '{raw_value}' — defaulting to 'other'")
        return RequirementCategory.OTHER


def _coerce_verification_type(raw_value) -> VerificationType:
    if not raw_value:
        return VerificationType.OTHER
    normalized = str(raw_value).strip().lower().replace(" ", "_").replace("-", "_")
    try:
        return VerificationType(normalized)
    except ValueError:
        logger.warning(f"Unrecognized verification_type '{raw_value}' — defaulting to 'other'")
        return VerificationType.OTHER


def _coerce_confidence(raw_value):
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, value))


def _coerce_required_documents(raw_value):
    if not raw_value:
        return []
    if isinstance(raw_value, list):
        return [str(item) for item in raw_value if item]
    return [str(raw_value)]


def _mark_failed(db, tender: Tender, message: str) -> None:
    logger.error(f"Tender {tender.id} processing failed: {message}")
    tender.processing_status = ProcessingStatus.FAILED
    tender.processing_error = message[:2000]
    db.commit()


def run_tender_processing_pipeline(tender_id: str) -> None:
    """Entry point invoked by FastAPI BackgroundTasks. Owns its own DB session."""
    db = SessionLocal()
    try:
        tender = db.query(Tender).filter(Tender.id == tender_id).first()
        if not tender:
            logger.error(f"Pipeline: tender {tender_id} not found")
            return

        if not tender.document_path:
            _mark_failed(db, tender, "No document uploaded for this tender")
            return

        # ---- Stage 1: text extraction (PyMuPDF, OCR fallback) ----
        tender.processing_status = ProcessingStatus.EXTRACTING_TEXT
        db.commit()

        try:
            extraction_result = document_processor.process_document(tender.document_path)
        except DocumentProcessingError as e:
            _mark_failed(db, tender, f"Text extraction failed: {e}")
            return
        except Exception as e:
            logger.error(f"Unexpected error during text extraction: {e}", exc_info=True)
            _mark_failed(db, tender, f"Unexpected error during text extraction: {e}")
            return

        raw_text = extraction_result["raw_text"]
        tender.extracted_text = raw_text
        tender.extraction_method = extraction_result["method"]
        tender.page_count = extraction_result["page_count"]
        tender.processing_status = ProcessingStatus.TEXT_EXTRACTED
        db.commit()

        if not raw_text or len(raw_text.strip()) < MIN_EXTRACTED_TEXT_CHARS:
            _mark_failed(db, tender, "No extractable text found in document, even after OCR fallback")
            return

        # ---- Stage 2: AI requirement extraction ----
        tender.processing_status = ProcessingStatus.EXTRACTING_REQUIREMENTS
        db.commit()

        try:
            candidates = ai_service.extract_requirements_from_text(raw_text)
        except AIExtractionError as e:
            _mark_failed(db, tender, f"AI extraction failed: {e}")
            return
        except Exception as e:
            logger.error(f"Unexpected error during AI extraction: {e}", exc_info=True)
            _mark_failed(db, tender, f"Unexpected error during AI extraction: {e}")
            return

        # Re-processing case: clear previously extracted requirements first.
        db.query(TenderRequirement).filter(TenderRequirement.tender_id == tender.id).delete()

        saved_count = 0
        for idx, item in enumerate(candidates):
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dict requirement candidate at index {idx}: {item!r}")
                continue

            description = (item.get("description") or "").strip()
            title = (item.get("title") or "").strip() or "Untitled Requirement"
            if not description:
                logger.warning(f"Skipping requirement candidate with empty description at index {idx}")
                continue

            confidence = _coerce_confidence(item.get("confidence"))
            mandatory_raw = item.get("mandatory")
            mandatory = bool(mandatory_raw) if mandatory_raw is not None else True

            needs_review = (
                confidence is None
                or confidence < CONFIDENCE_REVIEW_THRESHOLD
                or mandatory_raw is None
            )

            page_number = item.get("page_number")
            try:
                page_number = int(page_number) if page_number is not None else None
            except (TypeError, ValueError):
                page_number = None

            minimum_value = item.get("minimum_value")
            try:
                minimum_value = float(minimum_value) if minimum_value is not None else None
            except (TypeError, ValueError):
                minimum_value = None

            requirement = TenderRequirement(
                tender_id=tender.id,
                category=_coerce_category(item.get("category")),
                title=title[:500],
                description=description,
                clause_reference=item.get("clause_reference"),
                minimum_value=minimum_value,
                currency=item.get("currency"),
                period=item.get("period"),
                mandatory=mandatory,
                required_documents=_coerce_required_documents(item.get("required_documents")),
                verification_type=_coerce_verification_type(item.get("verification_type")),
                confidence=confidence,
                evidence=item.get("evidence"),
                page_number=page_number,
                needs_review=needs_review,
                extracted_by_ai=True,
                sequence_no=idx,
            )
            db.add(requirement)
            saved_count += 1

        tender.processing_status = ProcessingStatus.COMPLETED
        tender.processing_error = None
        db.commit()

        logger.info(
            f"Pipeline completed for tender {tender.tender_ref_no} ({tender.id}): "
            f"{saved_count}/{len(candidates)} requirements saved"
        )

    except Exception as e:
        # Absolute last-resort catch so a bug here never leaves a tender
        # stuck silently in an "extracting..." state forever.
        logger.error(f"Unhandled pipeline error for tender {tender_id}: {e}", exc_info=True)
        db.rollback()
        try:
            tender = db.query(Tender).filter(Tender.id == tender_id).first()
            if tender:
                tender.processing_status = ProcessingStatus.FAILED
                tender.processing_error = f"Unhandled pipeline error: {e}"[:2000]
                db.commit()
        except Exception:
            logger.error("Failed to record pipeline failure state", exc_info=True)
    finally:
        db.close()
