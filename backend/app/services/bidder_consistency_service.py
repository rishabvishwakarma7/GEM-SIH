"""
Bidder consistency service — cross-document analysis for a single bidder:

  1. Missing-document detection: compares the tender's mandatory,
     document-verified requirement categories against the document types
     the bidder has successfully uploaded and processed.
  2. Identity consistency checking: compares company_name / PAN / GSTIN
     values extracted from each of the bidder's documents and flags
     disagreements (e.g. GST certificate shows a different company name
     than the PAN card).

This is intentionally NOT the final compliance engine (no COMPLIANT /
NON-COMPLIANT verdict, no per-requirement evidence matching) — that is
explicitly Day 3+ scope. This module only surfaces missing documents and
identity red flags for the evaluator to review.

Called automatically at the end of the per-document pipeline
(bidder_document_service) and on demand via POST /api/bidders/{id}/analyze.
"""
import json
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models.bidder import Bidder, BidderDocument, DocumentProcessingStatus, BidderConsistencyStatus
from app.models.document import ExtractedDocumentData
from app.models.tender import TenderRequirement, VerificationType
from app.services.ai_service import BIDDER_DOCUMENT_TYPES
from app.core.logging_config import logger

# Fields compared pairwise across a bidder's documents for identity consistency.
IDENTITY_FIELDS = ["company_name", "pan", "gstin"]


def _normalize(value: str) -> str:
    return " ".join(value.strip().upper().split())


def _required_document_types(tender) -> set:
    """
    Mandatory, document-verified tender requirement categories that also
    correspond to a known bidder document type (categories like "identity"
    or "blacklist_debarment" don't map to an uploadable document and are
    skipped).
    """
    if not tender:
        return set()
    required = set()
    for req in tender.requirements:
        if not req.mandatory:
            continue
        if req.verification_type != VerificationType.DOCUMENT:
            continue
        category_value = req.category.value if hasattr(req.category, "value") else str(req.category)
        if category_value in BIDDER_DOCUMENT_TYPES:
            required.add(category_value)
    return required


def analyze_bidder(bidder_id: str, db: Optional[object] = None) -> None:
    """
    Recomputes and persists Bidder.consistency_report / missing_document_types
    / consistency_status / analyzed_at. Reuses the passed-in session if given
    (called from within the document pipeline's own session); otherwise opens
    and closes its own (for standalone/manual invocation).
    """
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    try:
        bidder = db.query(Bidder).filter(Bidder.id == bidder_id).first()
        if not bidder:
            logger.warning(f"analyze_bidder: bidder {bidder_id} not found")
            return

        documents = (
            db.query(BidderDocument).filter(BidderDocument.bidder_id == bidder.id).all()
        )

        completed_readable = []
        documents_failed = 0
        documents_needing_review = 0

        for doc in documents:
            if doc.processing_status == DocumentProcessingStatus.FAILED:
                documents_failed += 1
                continue
            if doc.processing_status != DocumentProcessingStatus.COMPLETED:
                continue

            extracted = (
                db.query(ExtractedDocumentData)
                .filter(ExtractedDocumentData.bidder_document_id == doc.id)
                .first()
            )
            if not extracted:
                continue
            if extracted.needs_review:
                documents_needing_review += 1
            if extracted.is_readable:
                completed_readable.append((doc, extracted))
            else:
                documents_failed += 1

        # ---- Missing-document detection ----
        required_types = _required_document_types(bidder.tender)
        uploaded_types = set()
        for doc, extracted in completed_readable:
            effective_type = extracted.detected_document_type or doc.document_type.value
            uploaded_types.add(effective_type)
        missing_documents = sorted(required_types - uploaded_types)

        # ---- Identity consistency checking ----
        identity_warnings = []
        field_values: dict = {field: [] for field in IDENTITY_FIELDS}  # field -> [(doc_type, raw_value)]

        for doc, extracted in completed_readable:
            try:
                fields = json.loads(extracted.structured_fields) if extracted.structured_fields else {}
            except (json.JSONDecodeError, TypeError):
                fields = {}
            effective_type = extracted.detected_document_type or doc.document_type.value
            for field in IDENTITY_FIELDS:
                value = fields.get(field)
                if value and isinstance(value, str) and value.strip():
                    field_values[field].append((effective_type, value.strip()))

        for field, entries in field_values.items():
            if len(entries) < 2:
                continue
            normalized_groups: dict = {}
            for doc_type, raw_value in entries:
                key = _normalize(raw_value)
                normalized_groups.setdefault(key, []).append(doc_type)
            if len(normalized_groups) > 1:
                involved_docs = sorted({dt for docs in normalized_groups.values() for dt in docs})
                distinct_values = list(normalized_groups.keys())
                identity_warnings.append({
                    "field": field,
                    "message": (
                        f"'{field}' differs across documents: "
                        + "; ".join(f"{v} ({', '.join(sorted(set(normalized_groups[v])))})" for v in distinct_values)
                    ),
                    "documents": involved_docs,
                })

        # ---- Rollup status ----
        if not completed_readable:
            status_value = BidderConsistencyStatus.NOT_ANALYZED
        elif identity_warnings:
            status_value = BidderConsistencyStatus.INCONSISTENT
        elif missing_documents or documents_needing_review > 0:
            status_value = BidderConsistencyStatus.NEEDS_REVIEW
        else:
            status_value = BidderConsistencyStatus.CONSISTENT

        report = {
            "missing_documents": missing_documents,
            "identity_warnings": identity_warnings,
            "documents_analyzed": len(completed_readable),
            "documents_failed": documents_failed,
            "documents_needing_review": documents_needing_review,
        }

        bidder.consistency_report = json.dumps(report)
        bidder.missing_document_types = missing_documents
        bidder.consistency_status = status_value
        bidder.analyzed_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"Bidder {bidder.id} analysis: status={status_value.value} "
            f"missing={len(missing_documents)} warnings={len(identity_warnings)}"
        )

    except Exception as e:
        logger.error(f"analyze_bidder failed for {bidder_id}: {e}", exc_info=True)
        db.rollback()
    finally:
        if owns_session:
            db.close()
