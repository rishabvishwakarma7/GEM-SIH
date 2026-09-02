"""
Document Risk Analysis Service (Upgrade — Task 3).

Analyses a single BidderDocument for suspicious signals using ONLY
deterministic heuristics — no AI call here.  AI may summarise the result
afterwards (see risk_intelligence_service.py), but the numeric risk_score
and every signal flag are computed in pure Python.

Signal catalogue and default weights (configurable via SIGNAL_WEIGHTS):
  METADATA_ANOMALY           +20  PDF creation/modification dates inconsistent
  DATE_INCONSISTENCY         +20  document date vs tender submission window
  IDENTIFIER_MISMATCH        +15  PAN/GSTIN/CIN differs from other docs
  REGISTRY_MISMATCH          +20  extracted value != verification provider result
  LOW_AI_CONFIDENCE          +15  overall extraction confidence < threshold
  TYPE_MISMATCH              +10  AI detected type != declared type

Risk level thresholds (also configurable):
  0–25   LOW
  26–50  MEDIUM
  51–75  HIGH
  76–100 CRITICAL
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF — already a dependency

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.bidder import Bidder, BidderDocument, DocumentProcessingStatus
from app.models.document import ExtractedDocumentData
from app.models.risk import DocumentRiskAnalysis, DocumentRiskLevel
from app.models.verification import VerificationResult, VerificationStatus
from app.core.logging_config import logger

# ---------------------------------------------------------------------------
# Configurable weights and thresholds
# ---------------------------------------------------------------------------
SIGNAL_WEIGHTS: Dict[str, int] = {
    "METADATA_ANOMALY": 20,
    "DATE_INCONSISTENCY": 20,
    "IDENTIFIER_MISMATCH": 15,
    "REGISTRY_MISMATCH": 20,
    "LOW_AI_CONFIDENCE": 15,
    "TYPE_MISMATCH": 10,
}

RISK_THRESHOLDS = [
    (76, DocumentRiskLevel.CRITICAL),
    (51, DocumentRiskLevel.HIGH),
    (26, DocumentRiskLevel.MEDIUM),
    (0, DocumentRiskLevel.LOW),
]

LOW_CONFIDENCE_THRESHOLD = 0.6


def _risk_level(score: float) -> DocumentRiskLevel:
    for threshold, level in RISK_THRESHOLDS:
        if score >= threshold:
            return level
    return DocumentRiskLevel.LOW


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


# ---------------------------------------------------------------------------
# Individual signal detectors
# ---------------------------------------------------------------------------

def _check_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """
    Inspect PDF metadata for anomalies:
    - modification date older than creation date
    - suspicious producer strings (common in document-forgery toolkits)
    - missing author/creator where expected
    """
    result = {
        "triggered": False,
        "signal": "METADATA_ANOMALY",
        "detail": "",
        "creation_date": None,
        "modification_date": None,
        "producer": None,
        "author": None,
    }
    try:
        doc = fitz.open(file_path)
        meta = doc.metadata or {}
        doc.close()

        creation_raw = meta.get("creationDate", "") or ""
        mod_raw = meta.get("modDate", "") or ""
        producer = (meta.get("producer") or "").strip()
        author = (meta.get("author") or "").strip()

        result["creation_date"] = creation_raw[:20] if creation_raw else None
        result["modification_date"] = mod_raw[:20] if mod_raw else None
        result["producer"] = producer or None
        result["author"] = author or None

        anomalies = []

        # Modification date before creation date is physically impossible
        def _parse_pdf_date(s: str) -> Optional[datetime]:
            # PDF date format: D:YYYYMMDDHHmmSSOHH'mm'
            try:
                s = s.replace("D:", "").split("+")[0].split("-")[0].split("Z")[0]
                s = s[:14]
                return datetime.strptime(s, "%Y%m%d%H%M%S")
            except Exception:
                return None

        if creation_raw and mod_raw:
            cd = _parse_pdf_date(creation_raw)
            md = _parse_pdf_date(mod_raw)
            if cd and md and md < cd:
                anomalies.append("Modification date precedes creation date")

        # Known suspicious producers (document editors often used in forgeries)
        suspicious_producers = [
            "inkscape", "scribus", "gimp", "paint", "unknown", "ghostscript"
        ]
        if producer and any(s in producer.lower() for s in suspicious_producers):
            anomalies.append(f"Suspicious PDF producer: '{producer}'")

        if anomalies:
            result["triggered"] = True
            result["detail"] = "; ".join(anomalies)

    except Exception as e:
        logger.warning(f"PDF metadata check failed for {file_path}: {e}")

    return result


def _check_date_consistency(
    extracted_fields: Dict[str, Any],
    file_kind: str,
) -> Dict[str, Any]:
    """
    Check that the document's issue/registration date is not in the future,
    and that validity/expiry dates have not already passed.
    """
    result = {"triggered": False, "signal": "DATE_INCONSISTENCY", "detail": ""}

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    anomalies = []

    date_fields = [
        ("registration_date", False),
        ("issue_date", False),
        ("valid_upto", True),   # True = expiry field
        ("expiry_date", True),
    ]

    for field, is_expiry in date_fields:
        raw = extracted_fields.get(field)
        if not raw or not isinstance(raw, str):
            continue
        # Try common formats
        parsed = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                parsed = datetime.strptime(raw.strip(), fmt)
                break
            except ValueError:
                continue
        if not parsed:
            continue

        if not is_expiry and parsed > now:
            anomalies.append(f"'{field}' ({raw}) is in the future — possible fabrication")
        if is_expiry and parsed < now:
            anomalies.append(f"Document expired: '{field}' was {raw}")

    if anomalies:
        result["triggered"] = True
        result["detail"] = "; ".join(anomalies)

    return result


def _check_identifier_consistency(
    extracted_fields: Dict[str, Any],
    bidder: Bidder,
    db: Session,
) -> Dict[str, Any]:
    """
    Cross-check PAN, GSTIN, company_name from this document against values
    extracted from the bidder's OTHER documents.  Mismatches are a red flag.
    """
    result = {"triggered": False, "signal": "IDENTIFIER_MISMATCH", "detail": ""}

    identity_fields = ["company_name", "pan", "gstin"]
    mismatches = []

    # Collect all extracted values from other completed documents
    for other_doc in bidder.documents:
        if not other_doc.extracted_data or not other_doc.extracted_data.is_readable:
            continue
        try:
            other_fields = json.loads(other_doc.extracted_data.structured_fields or "{}")
        except (json.JSONDecodeError, TypeError):
            other_fields = {}

        for field in identity_fields:
            this_val = extracted_fields.get(field)
            other_val = other_fields.get(field)
            if not this_val or not other_val:
                continue
            # Normalize for comparison
            n1 = " ".join(str(this_val).strip().upper().split())
            n2 = " ".join(str(other_val).strip().upper().split())
            if n1 != n2:
                mismatches.append(f"'{field}': '{this_val}' vs '{other_val}' (from another doc)")

    if mismatches:
        result["triggered"] = True
        result["detail"] = "; ".join(mismatches[:3])  # cap at 3 to avoid noise

    return result


def _check_registry_mismatch(
    bidder_document_id: str,
    requirement_id: Optional[str],
    db: Session,
) -> Dict[str, Any]:
    """
    If a VerificationResult exists for this document and its status is MISMATCH
    or NOT_FOUND, that is a strong risk signal.
    """
    result = {"triggered": False, "signal": "REGISTRY_MISMATCH", "detail": ""}

    vr: Optional[VerificationResult] = (
        db.query(VerificationResult)
        .filter(VerificationResult.bidder_document_id == bidder_document_id)
        .first()
    )
    if vr and vr.status in (VerificationStatus.MISMATCH, VerificationStatus.NOT_FOUND):
        result["triggered"] = True
        result["detail"] = (
            f"Registry provider '{vr.provider_name}' returned "
            f"'{vr.status.value}' for identifier '{vr.identifier_checked}'"
        )
    return result


def _check_low_confidence(extracted: ExtractedDocumentData) -> Dict[str, Any]:
    result = {"triggered": False, "signal": "LOW_AI_CONFIDENCE", "detail": ""}
    conf = extracted.confidence or 0.0
    if conf < LOW_CONFIDENCE_THRESHOLD:
        result["triggered"] = True
        result["detail"] = f"AI extraction confidence {conf:.2f} is below threshold {LOW_CONFIDENCE_THRESHOLD}"
    return result


def _check_type_mismatch(extracted: ExtractedDocumentData) -> Dict[str, Any]:
    result = {"triggered": False, "signal": "TYPE_MISMATCH", "detail": ""}
    if extracted.type_mismatch:
        result["triggered"] = True
        result["detail"] = (
            f"Declared document type does not match AI-detected type "
            f"'{extracted.detected_document_type}'"
        )
    return result


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------

def analyze_document_risk(
    document_id: str,
    db: Optional[Session] = None,
) -> Optional[DocumentRiskAnalysis]:
    """
    Runs all risk signals for one BidderDocument and upserts a
    DocumentRiskAnalysis row.  Returns the analysis record.

    Can be called inline (pass db) or standalone (owns its own session).
    """
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    try:
        doc: Optional[BidderDocument] = (
            db.query(BidderDocument).filter(BidderDocument.id == document_id).first()
        )
        if not doc:
            logger.warning(f"analyze_document_risk: document {document_id} not found")
            return None

        if doc.processing_status != DocumentProcessingStatus.COMPLETED:
            logger.info(f"Skipping risk analysis for {document_id} — not yet COMPLETED")
            return None

        extracted: Optional[ExtractedDocumentData] = doc.extracted_data
        try:
            fields = json.loads(extracted.structured_fields or "{}") if extracted else {}
        except (json.JSONDecodeError, TypeError):
            fields = {}

        # ---- Run all signal checks ----
        signals: List[Dict[str, Any]] = []
        total_score = 0.0

        flag_metadata = False
        flag_date = False
        flag_identifier = False
        flag_registry = False
        flag_confidence = False
        flag_type = False
        pdf_meta: Dict[str, Any] = {}

        # 1. PDF metadata (PDF only)
        if doc.file_kind == "pdf" and doc.file_path:
            meta_result = _check_pdf_metadata(doc.file_path)
            pdf_meta = meta_result
            if meta_result["triggered"]:
                weight = SIGNAL_WEIGHTS["METADATA_ANOMALY"]
                total_score += weight
                flag_metadata = True
                signals.append({
                    "signal": "METADATA_ANOMALY",
                    "weight": weight,
                    "detail": meta_result["detail"],
                })

        # 2. Date consistency
        date_result = _check_date_consistency(fields, doc.file_kind)
        if date_result["triggered"]:
            weight = SIGNAL_WEIGHTS["DATE_INCONSISTENCY"]
            total_score += weight
            flag_date = True
            signals.append({
                "signal": "DATE_INCONSISTENCY",
                "weight": weight,
                "detail": date_result["detail"],
            })

        # 3. Identifier consistency (needs bidder relationship)
        bidder: Optional[Bidder] = doc.bidder
        if bidder and extracted:
            id_result = _check_identifier_consistency(fields, bidder, db)
            if id_result["triggered"]:
                weight = SIGNAL_WEIGHTS["IDENTIFIER_MISMATCH"]
                total_score += weight
                flag_identifier = True
                signals.append({
                    "signal": "IDENTIFIER_MISMATCH",
                    "weight": weight,
                    "detail": id_result["detail"],
                })

        # 4. Registry mismatch
        reg_result = _check_registry_mismatch(str(doc.id), None, db)
        if reg_result["triggered"]:
            weight = SIGNAL_WEIGHTS["REGISTRY_MISMATCH"]
            total_score += weight
            flag_registry = True
            signals.append({
                "signal": "REGISTRY_MISMATCH",
                "weight": weight,
                "detail": reg_result["detail"],
            })

        # 5. Low AI confidence
        if extracted:
            conf_result = _check_low_confidence(extracted)
            if conf_result["triggered"]:
                weight = SIGNAL_WEIGHTS["LOW_AI_CONFIDENCE"]
                total_score += weight
                flag_confidence = True
                signals.append({
                    "signal": "LOW_AI_CONFIDENCE",
                    "weight": weight,
                    "detail": conf_result["detail"],
                })

            # 6. Type mismatch
            type_result = _check_type_mismatch(extracted)
            if type_result["triggered"]:
                weight = SIGNAL_WEIGHTS["TYPE_MISMATCH"]
                total_score += weight
                flag_type = True
                signals.append({
                    "signal": "TYPE_MISMATCH",
                    "weight": weight,
                    "detail": type_result["detail"],
                })

        final_score = _clamp(total_score)
        level = _risk_level(final_score)
        suspicious = final_score >= 26  # MEDIUM or above = flag as suspicious

        # ---- Upsert ----
        existing: Optional[DocumentRiskAnalysis] = (
            db.query(DocumentRiskAnalysis)
            .filter(DocumentRiskAnalysis.bidder_document_id == doc.id)
            .first()
        )
        record = existing or DocumentRiskAnalysis(bidder_document_id=doc.id)
        record.risk_score = final_score
        record.risk_level = level
        record.suspicious = suspicious
        record.suspicion_signals = json.dumps(signals)
        record.metadata_anomaly = flag_metadata
        record.date_inconsistency = flag_date
        record.identifier_mismatch = flag_identifier
        record.registry_mismatch = flag_registry
        record.low_ai_confidence = flag_confidence
        record.type_mismatch_flag = flag_type
        record.pdf_creation_date = pdf_meta.get("creation_date")
        record.pdf_modification_date = pdf_meta.get("modification_date")
        record.pdf_producer = pdf_meta.get("producer")
        record.pdf_author = pdf_meta.get("author")
        record.analyzed_at = datetime.utcnow()

        if not existing:
            db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(
            f"Document risk analysis for {doc.id}: score={final_score} "
            f"level={level.value} suspicious={suspicious} signals={len(signals)}"
        )
        return record

    except Exception as e:
        logger.error(f"Document risk analysis failed for {document_id}: {e}", exc_info=True)
        if db:
            db.rollback()
        return None
    finally:
        if owns_session and db:
            db.close()


document_risk_service = type("_Svc", (), {"analyze": staticmethod(analyze_document_risk)})()
