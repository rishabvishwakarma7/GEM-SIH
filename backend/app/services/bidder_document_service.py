"""
Bidder document extraction service — orchestrates the Bidder Document
Intelligence pipeline for a SINGLE uploaded document:

    document (PDF/image) -> document_processor -> raw text
                          -> ai_service          -> classification + structured fields
                          -> validated + persisted as ExtractedDocumentData

Runs as a FastAPI BackgroundTask, so it opens its own DB session. Every
stage updates BidderDocument.processing_status so the frontend can poll
GET /api/documents/{id}/status. Any exception at any stage is caught,
logged, and recorded on BidderDocument.processing_error rather than
crashing the background task silently.

After a document finishes (success or failure), the bidder-level
consistency/missing-document analysis is re-run automatically so the
bidder's `consistency_report` always reflects the latest set of documents.
"""
import json

from app.database import SessionLocal
from app.models.bidder import BidderDocument, DocumentProcessingStatus
from app.models.document import ExtractedDocumentData
from app.services.document_processor import document_processor, DocumentProcessingError
from app.services.ai_service import (
    ai_service,
    AIExtractionError,
    BIDDER_DOCUMENT_TYPES,
    EXPECTED_FIELDS_BY_TYPE,
)
from app.services.bidder_consistency_service import analyze_bidder
from app.core.logging_config import logger

# Upgrade services (imported lazily inside pipeline to avoid circular imports)
# document_risk_service, duplicate_detection_service, alert_service

CONFIDENCE_REVIEW_THRESHOLD = 0.6
MIN_EXTRACTED_TEXT_CHARS = 10


def _coerce_document_type(raw_value) -> str:
    if not raw_value:
        return "other"
    normalized = str(raw_value).strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in BIDDER_DOCUMENT_TYPES:
        return normalized
    logger.warning(f"Unrecognized bidder document_type '{raw_value}' — defaulting to 'other'")
    return "other"


def _coerce_confidence(raw_value):
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, value))


def _coerce_page_number(raw_value):
    try:
        return int(raw_value) if raw_value is not None else None
    except (TypeError, ValueError):
        return None


def _compute_missing_fields(document_type: str, fields: dict) -> list:
    expected = EXPECTED_FIELDS_BY_TYPE.get(document_type, EXPECTED_FIELDS_BY_TYPE["other"])
    missing = []
    for key in expected:
        value = fields.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(key)
    return missing


def _mark_failed(db, document: BidderDocument, message: str) -> None:
    logger.error(f"Bidder document {document.id} processing failed: {message}")
    document.processing_status = DocumentProcessingStatus.FAILED
    document.processing_error = message[:2000]
    db.commit()


def run_bidder_document_pipeline(document_id: str) -> None:
    """Entry point invoked by FastAPI BackgroundTasks. Owns its own DB session."""
    db = SessionLocal()
    bidder_id = None
    try:
        document = db.query(BidderDocument).filter(BidderDocument.id == document_id).first()
        if not document:
            logger.error(f"Pipeline: bidder document {document_id} not found")
            return
        bidder_id = str(document.bidder_id)

        if not document.file_path:
            _mark_failed(db, document, "No file stored for this document")
            return

        # ---- Stage 1: text extraction (PyMuPDF/OCR for PDFs, direct OCR for images) ----
        document.processing_status = DocumentProcessingStatus.EXTRACTING_TEXT
        db.commit()

        try:
            extraction_result = document_processor.process_bidder_document(
                document.file_path, document.file_kind
            )
        except DocumentProcessingError as e:
            _mark_failed(db, document, f"Text extraction failed: {e}")
            return
        except Exception as e:
            logger.error(f"Unexpected error during text extraction: {e}", exc_info=True)
            _mark_failed(db, document, f"Unexpected error during text extraction: {e}")
            return

        raw_text = extraction_result["raw_text"]
        document.extracted_text = raw_text
        document.extraction_method = extraction_result["method"]
        document.page_count = extraction_result["page_count"]
        document.processing_status = DocumentProcessingStatus.TEXT_EXTRACTED
        db.commit()

        # Existing ExtractedDocumentData is stale the moment we reprocess — clear it now
        # so a failure below doesn't leave old data alongside a "failed" status.
        db.query(ExtractedDocumentData).filter(
            ExtractedDocumentData.bidder_document_id == document.id
        ).delete()
        db.commit()

        if not raw_text or len(raw_text.strip()) < MIN_EXTRACTED_TEXT_CHARS:
            # Still save an ExtractedDocumentData row marking it unreadable, rather than
            # just failing outright — this is itself useful signal for the evaluator.
            unreadable = ExtractedDocumentData(
                bidder_document_id=document.id,
                detected_document_type="other",
                classification_confidence=0.0,
                type_mismatch=False,
                structured_fields=json.dumps({}),
                missing_fields=EXPECTED_FIELDS_BY_TYPE.get(document.document_type.value, []),
                confidence=0.0,
                evidence=None,
                page_number=None,
                is_readable=False,
                needs_review=True,
            )
            db.add(unreadable)
            document.processing_status = DocumentProcessingStatus.COMPLETED
            document.processing_error = "No extractable text found (document may be unreadable, blank, or too low-quality for OCR)"
            db.commit()
            logger.warning(f"Bidder document {document.id}: unreadable, no text extracted")
            return

        # ---- Stage 2: AI classification + structured extraction ----
        document.processing_status = DocumentProcessingStatus.EXTRACTING_DATA
        db.commit()

        try:
            result = ai_service.extract_bidder_document_fields(
                raw_text, declared_type=document.document_type.value
            )
        except AIExtractionError as e:
            _mark_failed(db, document, f"AI extraction failed: {e}")
            return
        except Exception as e:
            logger.error(f"Unexpected error during AI extraction: {e}", exc_info=True)
            _mark_failed(db, document, f"Unexpected error during AI extraction: {e}")
            return

        detected_type = _coerce_document_type(result.get("document_type"))
        classification_confidence = _coerce_confidence(result.get("classification_confidence"))
        fields = result.get("fields") if isinstance(result.get("fields"), dict) else {}
        confidence = _coerce_confidence(result.get("confidence"))
        is_readable = bool(result.get("is_readable", True))

        missing_fields = _compute_missing_fields(detected_type, fields)
        type_mismatch = detected_type != "other" and detected_type != document.document_type.value

        needs_review = (
            confidence is None
            or confidence < CONFIDENCE_REVIEW_THRESHOLD
            or not is_readable
            or type_mismatch
            or len(missing_fields) > 0
        )

        extracted = ExtractedDocumentData(
            bidder_document_id=document.id,
            detected_document_type=detected_type,
            classification_confidence=classification_confidence,
            type_mismatch=type_mismatch,
            structured_fields=json.dumps(fields),
            missing_fields=missing_fields,
            confidence=confidence,
            evidence=result.get("evidence"),
            page_number=_coerce_page_number(result.get("page_number")),
            is_readable=is_readable,
            needs_review=needs_review,
        )
        db.add(extracted)

        document.processing_status = DocumentProcessingStatus.COMPLETED
        document.processing_error = None
        db.commit()

        logger.info(
            f"Pipeline completed for bidder document {document.id} "
            f"({document.original_filename}): type={detected_type} confidence={confidence}"
        )

    except Exception as e:
        logger.error(f"Unhandled pipeline error for bidder document {document_id}: {e}", exc_info=True)
        db.rollback()
        try:
            document = db.query(BidderDocument).filter(BidderDocument.id == document_id).first()
            if document:
                document.processing_status = DocumentProcessingStatus.FAILED
                document.processing_error = f"Unhandled pipeline error: {e}"[:2000]
                db.commit()
        except Exception:
            logger.error("Failed to record pipeline failure state", exc_info=True)
    finally:
        # ---- Stage 3: refresh bidder-level consistency/missing-doc analysis ----
        try:
            if bidder_id:
                analyze_bidder(bidder_id, db=db)
        except Exception:
            logger.error(f"Failed to refresh consistency analysis for bidder {bidder_id}", exc_info=True)

        # ---- Stage 4 (Upgrade): document risk analysis ----
        try:
            if document_id:
                from app.services.document_risk_service import analyze_document_risk
                risk_record = analyze_document_risk(document_id, db=db)
                if risk_record:
                    # Emit document risk alerts if suspicious
                    try:
                        import json as _json
                        from app.services.alert_service import emit_document_risk_alerts
                        doc_for_alert = db.query(BidderDocument).filter(
                            BidderDocument.id == document_id
                        ).first()
                        if doc_for_alert:
                            signals = _json.loads(risk_record.suspicion_signals or "[]")
                            emit_document_risk_alerts(
                                db=db,
                                bidder_id=str(doc_for_alert.bidder_id),
                                tender_id=str(doc_for_alert.bidder.tender_id) if doc_for_alert.bidder else "",
                                document_id=str(document_id),
                                risk_score=risk_record.risk_score,
                                risk_level=risk_record.risk_level.value
                                if hasattr(risk_record.risk_level, "value")
                                else str(risk_record.risk_level),
                                signals=signals,
                            )
                    except Exception as ae:
                        logger.warning(f"Document risk alert emission failed: {ae}")
        except Exception as re:
            logger.warning(f"Document risk analysis post-pipeline failed for {document_id}: {re}")

        # ---- Stage 5 (Upgrade): duplicate detection ----
        try:
            if document_id:
                from app.services.duplicate_detection_service import run_duplicate_check_for_document
                matches = run_duplicate_check_for_document(document_id, db=db)
                if matches:
                    doc_for_dup = db.query(BidderDocument).filter(
                        BidderDocument.id == document_id
                    ).first()
                    if doc_for_dup:
                        from app.services.alert_service import emit_duplicate_alerts
                        for m in matches[:3]:  # cap alerts at 3 per document
                            emit_duplicate_alerts(
                                db=db,
                                tender_id=str(doc_for_dup.bidder.tender_id) if doc_for_dup.bidder else "",
                                bidder_id=str(doc_for_dup.bidder_id),
                                match_type=m.get("match_type", ""),
                                similarity=m.get("similarity_score", 0.0),
                                other_bidder_id=m.get("target_bidder_id", ""),
                            )
        except Exception as de:
            logger.warning(f"Duplicate detection post-pipeline failed for {document_id}: {de}")

        db.close()
