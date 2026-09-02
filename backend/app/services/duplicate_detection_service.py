"""
Duplicate Document Detection Service (Upgrade — Task 4).

Two-phase detection:
  Phase 1 — Exact match: compare SHA-256 hashes.
  Phase 2 — Similarity match: compare normalized text fingerprints using
             a fast character-level similarity ratio.

Both phases work across bidders within the same tender, and within the
same bidder's own document set.

IMPORTANT: Duplicate detection never produces a compliance verdict.
It only raises a flag for human review.
"""
import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.bidder import Bidder, BidderDocument, DocumentProcessingStatus
from app.models.risk import DuplicateDocumentMatch, DuplicateMatchType
from app.models.tender import Tender
from app.core.logging_config import logger

# Similarity thresholds (configurable)
THRESHOLDS = {
    DuplicateMatchType.EXACT: 1.0,             # SHA-256 exact match
    DuplicateMatchType.HIGH_SIMILARITY: 0.90,  # 90 %+
    DuplicateMatchType.POSSIBLE_SIMILARITY: 0.70,
    DuplicateMatchType.LOW_SIMILARITY: 0.0,    # catch-all (not persisted below MIN)
}
MIN_SIMILARITY_TO_PERSIST = 0.70   # don't store LOW_SIMILARITY matches


def compute_file_hash(file_path: str) -> Optional[str]:
    """Returns the SHA-256 hex digest of the file at file_path."""
    try:
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()
    except Exception as e:
        logger.warning(f"Could not hash file {file_path}: {e}")
        return None


def _normalize_text(text: str) -> str:
    """Strip whitespace, lowercase, remove punctuation for a stable fingerprint."""
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"[^a-z0-9]", "", t)
    return t


def compute_fingerprint(extracted_text: Optional[str]) -> Optional[str]:
    """
    Build a short stable fingerprint from the first 4 000 normalized chars of
    extracted text.  Used for quick similarity comparisons without storing the
    full text twice.
    """
    if not extracted_text:
        return None
    normalized = _normalize_text(extracted_text)
    return normalized[:4000]


def _similarity_ratio(a: str, b: str) -> float:
    """
    Fast character-level Sørensen–Dice similarity between two strings.
    O(n) using character bigrams.  Returns 0.0–1.0.
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    def bigrams(s: str):
        return {s[i:i+2] for i in range(len(s) - 1)}

    a_bi = bigrams(a)
    b_bi = bigrams(b)
    if not a_bi or not b_bi:
        return 0.0
    intersection = len(a_bi & b_bi)
    return (2.0 * intersection) / (len(a_bi) + len(b_bi))


def _match_type(score: float, exact: bool) -> DuplicateMatchType:
    if exact:
        return DuplicateMatchType.EXACT
    if score >= 0.97:
        return DuplicateMatchType.HIGH_SIMILARITY
    if score >= 0.90:
        return DuplicateMatchType.HIGH_SIMILARITY
    if score >= 0.70:
        return DuplicateMatchType.POSSIBLE_SIMILARITY
    return DuplicateMatchType.LOW_SIMILARITY


def _stable_pair(id_a: str, id_b: str) -> Tuple[str, str]:
    """Always return (smaller, larger) so we never store symmetric duplicates."""
    return (id_a, id_b) if id_a < id_b else (id_b, id_a)


def _update_document_hash_and_fingerprint(doc: BidderDocument, db: Session) -> bool:
    """
    Computes and stores file_hash + document_fingerprint on the BidderDocument
    row.  Returns True if any value was updated.
    """
    changed = False

    if not doc.file_hash and doc.file_path:
        doc.file_hash = compute_file_hash(doc.file_path)
        changed = True

    if not doc.document_fingerprint and doc.extracted_text:
        doc.document_fingerprint = compute_fingerprint(doc.extracted_text)
        changed = True
    elif not doc.document_fingerprint and doc.file_path:
        # Fallback: try reading extracted_data text
        if doc.extracted_data and doc.extracted_data.evidence:
            doc.document_fingerprint = compute_fingerprint(doc.extracted_data.evidence)
            changed = True

    if changed:
        db.commit()

    return changed


def run_duplicate_check_for_tender(
    tender_id: str,
    db: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """
    Runs duplicate detection across ALL bidder documents under a given tender.
    Returns a list of match summary dicts for the caller to act on.

    Upserts DuplicateDocumentMatch rows — safe to re-run.
    """
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    found: List[Dict[str, Any]] = []
    try:
        tender: Optional[Tender] = db.query(Tender).filter(Tender.id == tender_id).first()
        if not tender:
            logger.warning(f"Duplicate check: tender {tender_id} not found")
            return found

        # Collect all completed documents across all bidders
        all_docs: List[BidderDocument] = []
        for bidder in tender.bidders:
            for doc in bidder.documents:
                if doc.processing_status == DocumentProcessingStatus.COMPLETED:
                    _update_document_hash_and_fingerprint(doc, db)
                    all_docs.append(doc)

        # Pairwise comparison
        n = len(all_docs)
        for i in range(n):
            for j in range(i + 1, n):
                doc_a = all_docs[i]
                doc_b = all_docs[j]

                sid_a, sid_b = _stable_pair(str(doc_a.id), str(doc_b.id))

                # --- Phase 1: exact hash match ---
                exact = bool(
                    doc_a.file_hash
                    and doc_b.file_hash
                    and doc_a.file_hash == doc_b.file_hash
                )

                # --- Phase 2: text similarity ---
                sim_score = 0.0
                if doc_a.document_fingerprint and doc_b.document_fingerprint:
                    sim_score = _similarity_ratio(
                        doc_a.document_fingerprint, doc_b.document_fingerprint
                    )
                elif exact:
                    sim_score = 1.0

                # Only persist if meaningful
                final_score = 1.0 if exact else sim_score
                if final_score < MIN_SIMILARITY_TO_PERSIST:
                    continue

                match_type = _match_type(final_score, exact)

                # Upsert
                existing: Optional[DuplicateDocumentMatch] = (
                    db.query(DuplicateDocumentMatch)
                    .filter(
                        DuplicateDocumentMatch.source_document_id == sid_a,
                        DuplicateDocumentMatch.target_document_id == sid_b,
                    )
                    .first()
                )

                if existing:
                    record = existing
                else:
                    record = DuplicateDocumentMatch(
                        source_document_id=sid_a,
                        target_document_id=sid_b,
                    )
                    db.add(record)

                record.source_bidder_id = doc_a.bidder_id
                record.target_bidder_id = doc_b.bidder_id
                record.tender_id = tender.id
                record.similarity_score = round(final_score, 4)
                record.match_type = match_type
                record.exact_hash_match = exact
                record.detected_at = datetime.utcnow()
                db.commit()

                match_summary = {
                    "source_document_id": str(doc_a.id),
                    "target_document_id": str(doc_b.id),
                    "source_bidder_id": str(doc_a.bidder_id),
                    "target_bidder_id": str(doc_b.bidder_id),
                    "similarity_score": round(final_score * 100, 1),
                    "match_type": match_type.value,
                    "exact_hash_match": exact,
                }
                found.append(match_summary)
                logger.info(
                    f"Duplicate match: {doc_a.id} ↔ {doc_b.id} "
                    f"type={match_type.value} score={final_score:.3f}"
                )

        logger.info(
            f"Duplicate detection for tender {tender_id}: "
            f"{len(all_docs)} documents, {len(found)} matches found"
        )
        return found

    except Exception as e:
        logger.error(f"Duplicate detection failed for tender {tender_id}: {e}", exc_info=True)
        if db:
            db.rollback()
        return found
    finally:
        if owns_session and db:
            db.close()


def run_duplicate_check_for_document(
    document_id: str,
    db: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """
    Checks a single newly-processed document against all other docs in the
    same tender.  Called from the document pipeline after each document
    completes.
    """
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    found: List[Dict[str, Any]] = []
    try:
        doc: Optional[BidderDocument] = (
            db.query(BidderDocument).filter(BidderDocument.id == document_id).first()
        )
        if not doc:
            return found

        tender_id = str(doc.bidder.tender_id) if doc.bidder else None
        if not tender_id:
            return found

        _update_document_hash_and_fingerprint(doc, db)

        # Compare against all other completed docs in the same tender
        tender: Optional[Tender] = db.query(Tender).filter(Tender.id == tender_id).first()
        if not tender:
            return found

        others: List[BidderDocument] = []
        for bidder in tender.bidders:
            for other_doc in bidder.documents:
                if (
                    str(other_doc.id) != document_id
                    and other_doc.processing_status == DocumentProcessingStatus.COMPLETED
                ):
                    _update_document_hash_and_fingerprint(other_doc, db)
                    others.append(other_doc)

        for other_doc in others:
            sid_a, sid_b = _stable_pair(str(doc.id), str(other_doc.id))

            exact = bool(
                doc.file_hash and other_doc.file_hash and doc.file_hash == other_doc.file_hash
            )
            sim_score = 0.0
            if doc.document_fingerprint and other_doc.document_fingerprint:
                sim_score = _similarity_ratio(
                    doc.document_fingerprint, other_doc.document_fingerprint
                )
            elif exact:
                sim_score = 1.0

            final_score = 1.0 if exact else sim_score
            if final_score < MIN_SIMILARITY_TO_PERSIST:
                continue

            match_type = _match_type(final_score, exact)

            existing: Optional[DuplicateDocumentMatch] = (
                db.query(DuplicateDocumentMatch)
                .filter(
                    DuplicateDocumentMatch.source_document_id == sid_a,
                    DuplicateDocumentMatch.target_document_id == sid_b,
                )
                .first()
            )

            if existing:
                record = existing
            else:
                record = DuplicateDocumentMatch(
                    source_document_id=sid_a,
                    target_document_id=sid_b,
                )
                db.add(record)

            record.source_bidder_id = doc.bidder_id if doc.id == sid_a else other_doc.bidder_id
            record.target_bidder_id = other_doc.bidder_id if doc.id == sid_a else doc.bidder_id
            record.tender_id = tender.id
            record.similarity_score = round(final_score, 4)
            record.match_type = match_type
            record.exact_hash_match = exact
            record.detected_at = datetime.utcnow()
            db.commit()

            found.append({
                "source_document_id": str(doc.id),
                "target_document_id": str(other_doc.id),
                "similarity_score": round(final_score * 100, 1),
                "match_type": match_type.value,
                "exact_hash_match": exact,
            })

        return found

    except Exception as e:
        logger.error(f"Per-document duplicate check failed for {document_id}: {e}", exc_info=True)
        if db:
            db.rollback()
        return found
    finally:
        if owns_session and db:
            db.close()


duplicate_detection_service = type(
    "_Svc", (),
    {
        "run_for_tender": staticmethod(run_duplicate_check_for_tender),
        "run_for_document": staticmethod(run_duplicate_check_for_document),
        "compute_file_hash": staticmethod(compute_file_hash),
        "compute_fingerprint": staticmethod(compute_fingerprint),
    },
)()
